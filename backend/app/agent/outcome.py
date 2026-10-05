"""Terminal state and escalation reason derivation."""
from __future__ import annotations

from app.models import TerminalState, EscalationReason


def determine_outcome(
    is_refused: bool,
    escalation_reason: str | None,
    successful_mutation: str | None,
    patient_resolved: bool,
    active_intent: str | None
) -> tuple[str, str | None]:
    """Derive the terminal state and escalation reason based on the conversation state.

    Rules:
    - escalated + reason if escalate_to_human was called
    - refused if injection/bulk/admin request
    - booked/rescheduled/cancelled if the mutation succeeded
    - abandoned if nothing usable/happened
    """
    if is_refused:
        return TerminalState.refused, None
        
    if escalation_reason:
        return TerminalState.escalated, escalation_reason
        
    if successful_mutation:
        return successful_mutation, None
        
    # If we get here, no mutation happened and no escalation happened
    # Was there clear intent but the caller vanished or it's a closed day?
    return TerminalState.abandoned, None
