"""ClinicStore: loads clinic.json into a fresh in-memory SQLite DB.

Each /agent/run gets its own ClinicStore instance with isolated state.
All mutations are atomic (threading.Lock + SQLite transaction).
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from app.errors import ToolError


def _time_to_minutes(t: str) -> int:
    """Convert HH:MM to minutes since midnight."""
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _minutes_to_time(m: int) -> str:
    """Convert minutes since midnight to HH:MM."""
    return f"{m // 60:02d}:{m % 60:02d}"


DAY_MAP = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}


class ClinicStore:
    """Per-request clinic state backed by an in-memory SQLite database."""

    def __init__(self, clinic_json_path: str | Path):
        with open(clinic_json_path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

        self._lock = threading.RLock()
        self._db = sqlite3.connect(":memory:", check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._init_schema()
        self._load_data()

    def _init_schema(self):
        cur = self._db.cursor()
        cur.executescript("""
            CREATE TABLE clinic (
                id TEXT PRIMARY KEY,
                name TEXT,
                city TEXT,
                timezone TEXT,
                slot_minutes INTEGER,
                reference_date TEXT
            );
            CREATE TABLE doctors (
                id TEXT PRIMARY KEY,
                name TEXT,
                speciality TEXT
            );
            CREATE TABLE windows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id TEXT REFERENCES doctors(id),
                day TEXT,
                start TEXT,
                end TEXT
            );
            CREATE TABLE leave_dates (
                doctor_id TEXT REFERENCES doctors(id),
                date TEXT,
                PRIMARY KEY (doctor_id, date)
            );
            CREATE TABLE holidays (
                date TEXT PRIMARY KEY
            );
            CREATE TABLE patients (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone TEXT,
                dob TEXT
            );
            CREATE TABLE guardian_of (
                guardian_id TEXT REFERENCES patients(id),
                child_id TEXT REFERENCES patients(id),
                PRIMARY KEY (guardian_id, child_id)
            );
            CREATE TABLE appointments (
                id TEXT PRIMARY KEY,
                patient_id TEXT REFERENCES patients(id),
                doctor_id TEXT REFERENCES doctors(id),
                date TEXT,
                start TEXT,
                end TEXT,
                status TEXT DEFAULT 'booked'
            );
            CREATE UNIQUE INDEX idx_no_double_book
                ON appointments(doctor_id, date, start)
                WHERE status = 'booked';
        """)
        self._db.commit()

    def _load_data(self):
        cur = self._db.cursor()
        c = self._data["clinic"]
        cur.execute(
            "INSERT INTO clinic VALUES (?,?,?,?,?,?)",
            (c["id"], c["name"], c["city"], c["timezone"], c["slot_minutes"], c["reference_date"])
        )

        for doc in self._data["doctors"]:
            cur.execute("INSERT INTO doctors VALUES (?,?,?)", (doc["id"], doc["name"], doc["speciality"]))
            for w in doc["windows"]:
                cur.execute("INSERT INTO windows (doctor_id, day, start, end) VALUES (?,?,?,?)",
                           (doc["id"], w["day"], w["start"], w["end"]))
            for ld in doc.get("leave_dates", []):
                cur.execute("INSERT INTO leave_dates VALUES (?,?)", (doc["id"], ld))

        for h in self._data.get("holidays", []):
            cur.execute("INSERT INTO holidays VALUES (?)", (h,))

        for p in self._data["patients"]:
            cur.execute("INSERT INTO patients VALUES (?,?,?,?)", (p["id"], p["name"], p["phone"], p["dob"]))
            for child_id in p.get("guardian_of", []):
                cur.execute("INSERT INTO guardian_of VALUES (?,?)", (p["id"], child_id))

        for a in self._data["appointments"]:
            cur.execute("INSERT INTO appointments VALUES (?,?,?,?,?,?,?)",
                       (a["id"], a["patient_id"], a["doctor_id"], a["date"], a["start"], a["end"], a["status"]))

        self._db.commit()

    @property
    def slot_minutes(self) -> int:
        row = self._db.execute("SELECT slot_minutes FROM clinic LIMIT 1").fetchone()
        return row["slot_minutes"]

    # --- Doctor helpers ---

    def get_doctor(self, doctor_id: str) -> dict | None:
        row = self._db.execute("SELECT * FROM doctors WHERE id=?", (doctor_id,)).fetchone()
        return dict(row) if row else None

    def doctor_exists(self, doctor_id: str) -> bool:
        return self.get_doctor(doctor_id) is not None

    # --- Patient helpers ---

    def get_patient(self, patient_id: str) -> dict | None:
        row = self._db.execute("SELECT * FROM patients WHERE id=?", (patient_id,)).fetchone()
        if not row:
            return None
        p = dict(row)
        # Add guardian_of
        children = self._db.execute("SELECT child_id FROM guardian_of WHERE guardian_id=?", (patient_id,)).fetchall()
        p["guardian_of"] = [c["child_id"] for c in children]
        return p

    def patient_exists(self, patient_id: str) -> bool:
        return self.get_patient(patient_id) is not None

    # --- Slot generation ---

    def _get_merged_windows(self, doctor_id: str, day_name: str) -> list[tuple[int, int]]:
        """Get merged windows for a doctor on a given day name (Mon, Tue, etc.).
        Overlapping windows are merged so slots are never duplicated.
        """
        rows = self._db.execute(
            "SELECT start, end FROM windows WHERE doctor_id=? AND day=?",
            (doctor_id, day_name)
        ).fetchall()
        if not rows:
            return []

        # Convert to minutes and sort
        intervals = sorted((_time_to_minutes(r["start"]), _time_to_minutes(r["end"])) for r in rows)

        # Merge overlapping
        merged = [intervals[0]]
        for start, end in intervals[1:]:
            if start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        return merged

    def _generate_slots(self, doctor_id: str, day_name: str) -> list[str]:
        """Generate 15-min slots from merged windows. Last slot starts at end-15."""
        merged = self._get_merged_windows(doctor_id, day_name)
        slot_min = self.slot_minutes
        slots = []
        for start_m, end_m in merged:
            t = start_m
            while t + slot_min <= end_m:
                slots.append(_minutes_to_time(t))
                t += slot_min
        return sorted(set(slots))  # sorted, deduplicated

    def search_slots(self, doctor_id: str, date_str: str, today: str, period: str | None = None) -> dict:
        """Search free slots for a doctor on a date.

        Returns: {doctor_id, date, slots: [HH:MM], reason: null|code}
        """
        with self._lock:
            if not self.doctor_exists(doctor_id):
                raise ToolError("UNKNOWN_DOCTOR", f"Doctor {doctor_id} not found")

            d = date.fromisoformat(date_str)
            today_d = date.fromisoformat(today)

            result = {"doctor_id": doctor_id, "date": date_str, "slots": [], "reason": None}

            # Check past date
            if d < today_d:
                result["reason"] = "PAST_DATE"
                return result

            # Check holiday
            if self._db.execute("SELECT 1 FROM holidays WHERE date=?", (date_str,)).fetchone():
                result["reason"] = "HOLIDAY"
                return result

            # Check leave
            if self._db.execute("SELECT 1 FROM leave_dates WHERE doctor_id=? AND date=?",
                               (doctor_id, date_str)).fetchone():
                result["reason"] = "DOCTOR_ON_LEAVE"
                return result

            # Get weekday
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            day_name = day_names[d.weekday()]

            all_slots = self._generate_slots(doctor_id, day_name)
            if not all_slots:
                result["reason"] = "NOT_A_WORKING_DAY"
                return result

            # Filter by booked appointments
            booked = self._db.execute(
                "SELECT start FROM appointments WHERE doctor_id=? AND date=? AND status='booked'",
                (doctor_id, date_str)
            ).fetchall()
            booked_set = {r["start"] for r in booked}
            free_slots = [s for s in all_slots if s not in booked_set]

            # Filter by period
            if period:
                free_slots = self._filter_by_period(free_slots, period)

            result["slots"] = sorted(free_slots)
            return result

    def _filter_by_period(self, slots: list[str], period: str) -> list[str]:
        """morning < 12:00, afternoon 12:00-16:00, evening >= 16:00"""
        filtered = []
        for s in slots:
            mins = _time_to_minutes(s)
            if period == "morning" and mins < 720:
                filtered.append(s)
            elif period == "afternoon" and 720 <= mins < 960:
                filtered.append(s)
            elif period == "evening" and mins >= 960:
                filtered.append(s)
        return filtered

    # --- Appointment operations ---

    def _next_appointment_id(self) -> str:
        row = self._db.execute("SELECT id FROM appointments ORDER BY id DESC LIMIT 1").fetchone()
        if row:
            num = int(row["id"].split("_")[1]) + 1
        else:
            num = 1
        return f"ap_{num:04d}"

    def book_appointment(self, patient_id: str, doctor_id: str, date: str, start: str, today: str) -> dict:
        """Book an appointment. Thread-safe with lock + unique constraint."""
        import datetime
        with self._lock:
            if not self.patient_exists(patient_id):
                raise ToolError("UNKNOWN_PATIENT", f"Patient {patient_id} not found")
            if not self.doctor_exists(doctor_id):
                raise ToolError("UNKNOWN_DOCTOR", f"Doctor {doctor_id} not found")

            # Check slot validity
            slot_result = self.search_slots(doctor_id, date, today)
            if slot_result["reason"]:
                raise ToolError(slot_result["reason"], f"Cannot book: {slot_result['reason']}", hint=f"Date {date} is unavailable for {doctor_id}")

            if start not in slot_result["slots"]:
                # Check if slot exists at all in the grid
                d = datetime.date.fromisoformat(date)
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                all_slots = self._generate_slots(doctor_id, day_names[d.weekday()])
                if start not in all_slots:
                    raise ToolError("NOT_A_SLOT", f"{start} is not a valid slot for {doctor_id} on {date}",
                                  hint=f"Valid slots: {', '.join(slot_result['slots'][:5])}")
                else:
                    raise ToolError("SLOT_TAKEN", f"{start} on {date} is already booked",
                                  hint=f"Available: {', '.join(slot_result['slots'][:5])}")

            end_mins = _time_to_minutes(start) + self.slot_minutes
            end = _minutes_to_time(end_mins)

            ap_id = self._next_appointment_id()
            try:
                self._db.execute(
                    "INSERT INTO appointments (id, patient_id, doctor_id, date, start, end, status) VALUES (?,?,?,?,?,?,?)",
                    (ap_id, patient_id, doctor_id, date, start, end, "booked")
                )
                self._db.commit()
            except sqlite3.IntegrityError:
                raise ToolError("SLOT_TAKEN", f"Race condition: {start} on {date} was just taken")

            return {
                "id": ap_id, "patient_id": patient_id, "doctor_id": doctor_id,
                "date": date, "start": start, "end": end, "status": "booked"
            }

    def reschedule_appointment(self, appointment_id: str, new_date: str, new_start: str, today: str) -> dict:
        """Reschedule: atomic move. Old slot freed, new slot taken in one transaction."""
        with self._lock:
            row = self._db.execute("SELECT * FROM appointments WHERE id=?", (appointment_id,)).fetchone()
            if not row:
                raise ToolError("UNKNOWN_APPOINTMENT", f"Appointment {appointment_id} not found")
            apt = dict(row)

            if apt["status"] == "cancelled":
                raise ToolError("ALREADY_CANCELLED", f"Cannot reschedule a cancelled appointment")

            # Check new slot validity
            slot_result = self.search_slots(apt["doctor_id"], new_date, today)
            if slot_result["reason"]:
                raise ToolError(slot_result["reason"], f"Cannot reschedule to {new_date}: {slot_result['reason']}")

            if new_start not in slot_result["slots"]:
                d = date.fromisoformat(new_date)
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                all_slots = self._generate_slots(apt["doctor_id"], day_names[d.weekday()])
                if new_start not in all_slots:
                    raise ToolError("NOT_A_SLOT", f"{new_start} is not a valid slot on {new_date}")
                else:
                    raise ToolError("SLOT_TAKEN", f"{new_start} on {new_date} is already booked")

            new_end = _minutes_to_time(_time_to_minutes(new_start) + self.slot_minutes)

            try:
                # Cancel old, book new in one transaction
                self._db.execute(
                    "UPDATE appointments SET status='cancelled' WHERE id=?",
                    (appointment_id,)
                )
                new_id = self._next_appointment_id()
                self._db.execute(
                    "INSERT INTO appointments (id, patient_id, doctor_id, date, start, end, status) VALUES (?,?,?,?,?,?,?)",
                    (new_id, apt["patient_id"], apt["doctor_id"], new_date, new_start, new_end, "booked")
                )
                self._db.commit()
            except sqlite3.IntegrityError:
                self._db.rollback()
                raise ToolError("SLOT_TAKEN", f"Race: {new_start} on {new_date} was just taken")

        return {
            "id": new_id, "patient_id": apt["patient_id"], "doctor_id": apt["doctor_id"],
            "date": new_date, "start": new_start, "end": new_end, "status": "booked",
            "old_appointment_id": appointment_id
        }

    def cancel_appointment(self, appointment_id: str) -> dict:
        """Cancel an appointment. Cancelling twice -> ALREADY_CANCELLED."""
        with self._lock:
            row = self._db.execute("SELECT * FROM appointments WHERE id=?", (appointment_id,)).fetchone()
            if not row:
                raise ToolError("UNKNOWN_APPOINTMENT", f"Appointment {appointment_id} not found")
            apt = dict(row)

            if apt["status"] == "cancelled":
                raise ToolError("ALREADY_CANCELLED", f"Appointment {appointment_id} is already cancelled")

            self._db.execute("UPDATE appointments SET status='cancelled' WHERE id=?", (appointment_id,))
            self._db.commit()

        apt["status"] = "cancelled"
        return apt

    # --- Patient lookup ---

    def lookup_patient(self, name: str | None = None, phone: str | None = None, dob: str | None = None) -> dict:
        """Lookup patients by name/phone/dob. Returns candidates, never picks one.

        Matching rules:
        - Phone: exact match after normalizing (strip +91, spaces, dashes)
        - Name: case-insensitive, whitespace-normalized, but "R. K. Sharma" != "Rajesh Kumar Sharma"
        - Name + phone: narrow to one
        - Name alone or phone alone: may return many
        - NEVER auto-picks when multiple remain
        """
        # Normalize phone
        norm_phone = None
        if phone:
            norm_phone = phone.replace("+91", "").replace("-", "").replace(" ", "").strip()
            # Handle Devanagari digits
            devanagari = "०१२३४५६७८९"
            for i, ch in enumerate(devanagari):
                norm_phone = norm_phone.replace(ch, str(i))

        candidates = []
        query = "SELECT * FROM patients WHERE 1=1"
        params: list = []

        def _name_matches(db_name: str, search_name: str) -> bool:
            norm_db = self._normalize_name(db_name)
            norm_search = self._normalize_name(search_name)
            if norm_db == norm_search:
                return True
            # Surname match
            if norm_search == norm_db.split()[-1]:
                return True
            # All parts match (e.g. "Rajesh Sharma" matches "Rajesh Kumar Sharma")
            search_parts = norm_search.split()
            db_parts = norm_db.split()
            return all(sp in db_parts for sp in search_parts)

        if norm_phone and name:
            # Both: narrow match
            query += " AND phone=?"
            params.append(norm_phone)
            rows = self._db.execute(query, params).fetchall()
            # Filter by name flexibly. Remove phone-only fallback!
            candidates = [dict(r) for r in rows if _name_matches(r["name"], name)]
        elif norm_phone:
            query += " AND phone=?"
            params.append(norm_phone)
            rows = self._db.execute(query, params).fetchall()
            candidates = [dict(r) for r in rows]
        elif name:
            rows = self._db.execute("SELECT * FROM patients", []).fetchall()
            candidates = [dict(r) for r in rows if _name_matches(r["name"], name)]
        elif dob:
            query += " AND dob=?"
            params.append(dob)
            rows = self._db.execute(query, params).fetchall()
            candidates = [dict(r) for r in rows]
        else:
            return {"candidates": [], "match": "none"}

        # Add guardian_of for each candidate
        for c in candidates:
            children = self._db.execute("SELECT child_id FROM guardian_of WHERE guardian_id=?", (c["id"],)).fetchall()
            c["guardian_of"] = [ch["child_id"] for ch in children]

        if len(candidates) == 0:
            match = "none"
        elif len(candidates) == 1:
            match = "exact"
        else:
            match = "multiple"

        return {"candidates": candidates, "match": match}

    def _normalize_name(self, name: str) -> str:
        """Normalize name for comparison: lowercase, collapse whitespace.
        Does NOT strip dots or expand initials — R.K. Sharma != Rajesh Kumar Sharma.
        """
        return " ".join(name.lower().split())

    # --- List appointments helper ---

    def list_appointments(self, patient_id: str, date_str: str | None = None) -> list[dict]:
        """List booked appointments for a patient, optionally filtered by date."""
        query = "SELECT * FROM appointments WHERE patient_id=? AND status='booked'"
        params: list = [patient_id]
        if date_str:
            query += " AND date=?"
            params.append(date_str)
        rows = self._db.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_appointment(self, appointment_id: str) -> dict | None:
        row = self._db.execute("SELECT * FROM appointments WHERE id=?", (appointment_id,)).fetchone()
        return dict(row) if row else None

    # --- Escalate ---

    def escalate_to_human(self, reason: str, detail: str, patient_id: str | None = None) -> dict:
        """Record an escalation. Returns a handoff record."""
        valid_reasons = {"clinical_urgent", "medical_advice", "not_authorised", "ambiguous_patient", "out_of_scope"}
        if reason not in valid_reasons:
            raise ToolError("INVALID_REASON", f"reason must be one of {sorted(valid_reasons)}")
        return {"handoff_id": "handoff_001", "status": "open", "reason": reason, "detail": detail, "patient_id": patient_id}
