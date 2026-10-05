"""lookup_patient tool: resolve a caller to patient record(s)."""
from __future__ import annotations
from app.tools.store import ClinicStore


def lookup_patient(store: ClinicStore, name: str | None = None, phone: str | None = None, dob: str | None = None) -> dict:
    """Lookup patient by name/phone/dob. Returns candidates, never picks one."""
    return store.lookup_patient(name, phone, dob)
