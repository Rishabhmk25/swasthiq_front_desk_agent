"""Pydantic models: API request/response, enums, tool argument models, TurnFrame."""
from __future__ import annotations

import re
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# --- Enums ---

class TerminalState(str, Enum):
    booked = "booked"
    rescheduled = "rescheduled"
    cancelled = "cancelled"
    escalated = "escalated"
    refused = "refused"
    abandoned = "abandoned"


class EscalationReason(str, Enum):
    clinical_urgent = "clinical_urgent"
    medical_advice = "medical_advice"
    not_authorised = "not_authorised"
    ambiguous_patient = "ambiguous_patient"
    out_of_scope = "out_of_scope"


class Period(str, Enum):
    morning = "morning"
    afternoon = "afternoon"
    evening = "evening"


# --- API Request / Response ---

class AgentRequest(BaseModel):
    conversation_id: str
    today: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    turns: list[str] = Field(..., max_length=30)

    @field_validator("today")
    @classmethod
    def validate_today(cls, v: str) -> str:
        from datetime import date
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Invalid date format or value for today: {v}")
        return v

    @field_validator("turns")
    @classmethod
    def validate_turns(cls, v: list[str]) -> list[str]:
        for i, turn in enumerate(v):
            if len(turn) > 2000:
                raise ValueError(f"Turn {i} exceeds 2000 characters")
        return v


class ToolCallRecord(BaseModel):
    name: str
    arguments: dict[str, Any]


class MetricsRecord(BaseModel):
    turns: int = 0
    tokens: int = 0
    latency_ms: int = 0


class AgentResponse(BaseModel):
    conversation_id: str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    terminal_state: str
    escalation_reason: Optional[str] = None
    patient_id: Optional[str] = None
    appointment_id: Optional[str] = None
    reply: str = ""
    metrics: MetricsRecord = Field(default_factory=MetricsRecord)


# --- Tool Argument Models (strict: extra fields forbidden) ---

ISO_DATE = r"^\d{4}-\d{2}-\d{2}$"
HH_MM = r"^\d{2}:\d{2}$"
DR_ID = r"^dr_\w+$"
PT_ID = r"^pt_\d{4}$"
AP_ID = r"^ap_\d{4}$"


class SearchSlotsArgs(BaseModel):
    model_config = {"extra": "forbid"}
    doctor_id: str = Field(..., pattern=DR_ID)
    date: str = Field(..., pattern=ISO_DATE)
    period: Optional[str] = None

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("morning", "afternoon", "evening"):
            raise ValueError(f"period must be morning|afternoon|evening, got {v}")
        return v


class BookAppointmentArgs(BaseModel):
    model_config = {"extra": "forbid"}
    patient_id: str = Field(..., pattern=PT_ID)
    doctor_id: str = Field(..., pattern=DR_ID)
    date: str = Field(..., pattern=ISO_DATE)
    start: str = Field(..., pattern=HH_MM)


class RescheduleAppointmentArgs(BaseModel):
    model_config = {"extra": "forbid"}
    appointment_id: str = Field(..., pattern=AP_ID)
    new_date: str = Field(..., pattern=ISO_DATE)
    new_start: str = Field(..., pattern=HH_MM)


class CancelAppointmentArgs(BaseModel):
    model_config = {"extra": "forbid"}
    appointment_id: str = Field(..., pattern=AP_ID)


class LookupPatientArgs(BaseModel):
    model_config = {"extra": "forbid"}
    name: Optional[str] = None
    phone: Optional[str] = None
    dob: Optional[str] = None


class EscalateToHumanArgs(BaseModel):
    model_config = {"extra": "forbid"}
    reason: str
    detail: str = ""
    patient_id: Optional[str] = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        valid = {"clinical_urgent", "medical_advice", "not_authorised", "ambiguous_patient", "out_of_scope"}
        if v not in valid:
            raise ValueError(f"reason must be one of {sorted(valid)}, got {v}")
        return v


# --- Turn Frame (extraction result from NLU) ---

class TurnFrame(BaseModel):
    """Result of parsing a single caller turn."""
    intent: Optional[str] = None  # book|reschedule|cancel|medical_advice|clinical_symptom|out_of_scope|injection|noise|unknown
    doctor: Optional[str] = None  # dr_rao or dr_sethi
    date_raw: Optional[str] = None  # raw phrase like "kal", "parso", "3 tareekh"
    date_iso: Optional[str] = None  # resolved ISO date
    time_raw: Optional[str] = None  # raw phrase like "gyarah baje", "10:30"
    time_hhmm: Optional[str] = None  # resolved HH:MM
    period: Optional[str] = None  # morning|afternoon|evening
    patient_name: Optional[str] = None
    phone: Optional[str] = None
    relation: Optional[str] = None  # beta, beti, etc.
    beneficiary_name: Optional[str] = None  # the person the appointment is for
    red_flag: bool = False
    red_flag_phrase: Optional[str] = None
    medical_advice: bool = False
    injection: bool = False
    out_of_scope: bool = False
    noise: bool = False
    correction_seen: bool = False
    warnings: list[str] = Field(default_factory=list)
    llm_fallback: bool = False
