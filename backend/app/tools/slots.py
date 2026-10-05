"""search_slots tool: find free slots for a doctor on a date."""
from __future__ import annotations
from app.tools.store import ClinicStore


def search_slots(store: ClinicStore, doctor_id: str, date: str, today: str, period: str | None = None) -> dict:
    """Search free slots. Pure data, no LLM."""
    return store.search_slots(doctor_id, date, today, period)
