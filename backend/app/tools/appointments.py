"""Appointment tools: book, reschedule, cancel."""
from __future__ import annotations
from app.tools.store import ClinicStore


def book_appointment(store: ClinicStore, patient_id: str, doctor_id: str, date: str, start: str, today: str) -> dict:
    """Book an appointment in a free slot."""
    return store.book_appointment(patient_id, doctor_id, date, start, today)


def reschedule_appointment(store: ClinicStore, appointment_id: str, new_date: str, new_start: str, today: str) -> dict:
    """Reschedule an existing appointment atomically."""
    return store.reschedule_appointment(appointment_id, new_date, new_start, today)


def cancel_appointment(store: ClinicStore, appointment_id: str) -> dict:
    """Cancel an existing appointment."""
    return store.cancel_appointment(appointment_id)
