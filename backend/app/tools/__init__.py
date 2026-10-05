"""TOOLS registry: name -> (ArgsModel, fn). REST router POST /tools/{name}."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.errors import ToolError
from app.models import (
    SearchSlotsArgs, BookAppointmentArgs, RescheduleAppointmentArgs,
    CancelAppointmentArgs, LookupPatientArgs, EscalateToHumanArgs,
)

router = APIRouter(prefix="/tools", tags=["tools"])

# Tool registry: name -> ArgsModel class
TOOLS = {
    "search_slots": SearchSlotsArgs,
    "book_appointment": BookAppointmentArgs,
    "reschedule_appointment": RescheduleAppointmentArgs,
    "cancel_appointment": CancelAppointmentArgs,
    "lookup_patient": LookupPatientArgs,
    "escalate_to_human": EscalateToHumanArgs,
}
