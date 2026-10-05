"""Structured error types for the tool layer."""
from __future__ import annotations


class ToolError(Exception):
    """A tool call failed with a specific, machine-readable code.

    Attributes:
        code: Stable machine code (e.g. SLOT_TAKEN, NOT_A_SLOT, ALREADY_CANCELLED).
        message: Human-readable explanation.
        hint: Actionable guidance for the agent or caller.
    """

    def __init__(self, code: str, message: str, hint: str = ""):
        self.code = code
        self.message = message
        self.hint = hint
        super().__init__(f"{code}: {message}")

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "hint": self.hint}
