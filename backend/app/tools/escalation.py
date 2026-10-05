"""escalate_to_human tool: hand the conversation off to a human."""
from __future__ import annotations
from app.tools.store import ClinicStore


def escalate_to_human(store: ClinicStore, reason: str, detail: str, patient_id: str | None = None) -> dict:
    """Record an escalation to a human operator."""
    return store.escalate_to_human(reason, detail, patient_id)
