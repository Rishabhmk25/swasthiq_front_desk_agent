"""Orchestrator: per-turn state machine and tool execution.

Implements the safety pre-scan (commit-last rule), slot filling,
patient resolution, authorization, and execution of tools.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.agent.nlu_llm import Extractor
from app.agent.safety import check_safety
from app.agent.guard import GroundingGuard
from app.agent import replies
from app.agent.outcome import determine_outcome
from app.errors import ToolError
from app.models import AgentRequest, AgentResponse, ToolCallRecord, TurnFrame
from app.models import LookupPatientArgs, SearchSlotsArgs, BookAppointmentArgs, RescheduleAppointmentArgs, CancelAppointmentArgs, EscalateToHumanArgs
from pydantic import ValidationError
from app.tools.store import ClinicStore


@dataclass
class ConversationState:
    intent: str | None = None
    doctor: str | None = None
    date_iso: str | None = None
    time_hhmm: str | None = None
    period: str | None = None
    caller_name: str | None = None
    caller_phone: str | None = None
    beneficiary_relation: str | None = None
    beneficiary_name: str | None = None
    beneficiary_verified: bool = False
    
    # Resolved entities
    resolved_patient_id: str | None = None
    target_appointment_id: str | None = None
    last_search_result: dict | None = None
    last_search_key: str | None = None
    
    # Outcomes
    is_refused: bool = False
    escalation_reason: str | None = None
    successful_mutation: str | None = None
    mutated_appointment_id: str | None = None
    mutated_patient_id: str | None = None
    
    # Internal flags
    abandoned_reason: str | None = None


def run_conversation(request: AgentRequest, store: ClinicStore, extractor: Extractor) -> tuple[AgentResponse, list[dict]]:
    """Run a full conversation over a fresh ClinicStore."""
    today = date.fromisoformat(request.today)
    state = ConversationState()
    guard = GroundingGuard()
    tool_calls: list[ToolCallRecord] = []
    trace: list[dict] = []
    
    total_tokens = 0
    total_latency = 0
    reply_text = replies.noop()
    
    # --- 1. SAFETY PRE-SCAN (Commit-Last Rule) ---
    # Because all turns arrive at once, check them all before any mutation.
    for text in request.turns:
        safety = check_safety(text)
        if safety["red_flag"]:
            tc = ToolCallRecord(name="escalate_to_human", arguments={
                "reason": "clinical_urgent",
                "detail": "Escalated by orchestrator pre-scan"
            })
            tool_calls.append(tc)
            try:
                res = store.escalate_to_human(**tc.arguments)
                trace.append({"type": "tool", "name": "escalate_to_human", "args": tc.arguments, "result": res})
            except ToolError:
                pass
            
            response = AgentResponse(
                conversation_id=request.conversation_id,
                tool_calls=tool_calls,
                terminal_state="escalated",
                escalation_reason="clinical_urgent",
                patient_id=None,
                appointment_id=None,
                reply=replies.handoff_clinical(),
            )
            response.metrics.turns = len(request.turns)
            response.metrics.tokens = 0
            response.metrics.latency_ms = 0
            return response, trace

    # --- 2. PER-TURN PROCESSING ---
    history: list[str] = []
    
    for text in request.turns:
        if state.is_refused or (state.escalation_reason and state.escalation_reason != "clinical_urgent"):
            # If already refused or escalated (non-urgent), we can stop processing turns.
            # (If it's urgent, we still want to process quickly but not mutate)
            break
            
        # If it's urgent, we know we will escalate, but we might still extract for logging.
        
        frame, metrics = extractor.extract(text, history, today)
        total_tokens += metrics["tokens"]
        total_latency += metrics["latency_ms"]
        
        trace.append({
            "type": "caller",
            "text": text,
            "frame": frame.model_dump()
        })
        
        # Apply safety from this turn (if pre-scan missed it or for other reasons)
        if frame.red_flag:
            state.escalation_reason = "clinical_urgent"
            reply_text = replies.handoff_clinical()
            break
        elif frame.injection:
            state.is_refused = True
            reply_text = replies.refused()
            break
        elif frame.medical_advice:
            state.escalation_reason = "medical_advice"
            reply_text = replies.handoff_medical_advice()
            break
        elif frame.out_of_scope:
            state.escalation_reason = "out_of_scope"
            reply_text = replies.handoff_out_of_scope()
            break
            
        if frame.noise:
            history.append(f"Caller: {text}")
            history.append(f"Agent: Ji, bataiye?")
            continue
            
        # Update state (slot filling)
        if frame.intent: state.intent = frame.intent
        if frame.doctor: state.doctor = frame.doctor
        if frame.date_iso: state.date_iso = frame.date_iso
        if frame.time_hhmm: state.time_hhmm = frame.time_hhmm
        if frame.period: state.period = frame.period
        if frame.patient_name: state.caller_name = frame.patient_name
        if frame.phone: state.caller_phone = frame.phone
        if frame.relation: state.beneficiary_relation = frame.relation
        if frame.beneficiary_name: state.beneficiary_name = frame.beneficiary_name
        
        if frame.correction_seen:
            # The NLU rule handles replacing the specific field
            pass

        # --- 3. TOOL EXECUTION ---
        
        # A. Patient Lookup & Authorization
        if (state.caller_name or state.caller_phone) and not state.resolved_patient_id:
            try:
                tc = ToolCallRecord(name="lookup_patient", arguments={
                    "name": state.caller_name, "phone": state.caller_phone
                })
                # Remove None values
                tc.arguments = {k: v for k, v in tc.arguments.items() if v is not None}
                try:
                    LookupPatientArgs(**tc.arguments)
                except ValidationError as e:
                    raise ToolError("VALIDATION_ERROR", str(e))
                tool_calls.append(tc)
                
                res = store.lookup_patient(**tc.arguments)
                guard.add_tool_result("lookup_patient", res)
                trace.append({"type": "tool", "name": "lookup_patient", "args": tc.arguments, "result": res})
                
                if res["match"] == "exact":
                    # Tier 2 Audit §3.1: Require BOTH name and phone for any mutation
                    if not state.caller_name or not state.caller_phone:
                        if not state.caller_name:
                            reply_text = replies.ambiguous_name()
                        elif not state.caller_phone:
                            reply_text = replies.ambiguous_phone()
                    else:
                        state.resolved_patient_id = res["candidates"][0]["id"]
                        
                elif res["match"] == "multiple":
                    # Mid-loop, we just ask for the missing info.
                    # We will escalate at the end of the loop if still unresolved.
                    if not state.caller_phone:
                        reply_text = replies.ambiguous_phone()
                    elif not state.caller_name:
                        reply_text = replies.ambiguous_name()
                    else:
                        state.escalation_reason = "ambiguous_patient"
                        reply_text = replies.handoff_ambiguous()
                        break
                        
                elif res["match"] == "none":
                    if state.caller_name and state.caller_phone:
                        # Mid-loop, we can escalate immediately
                        state.escalation_reason = "not_authorised"
                        reply_text = replies.handoff_not_authorised()
                        break
                    else:
                        reply_text = replies.patient_not_found(state.caller_name or state.caller_phone)
                    
            except ToolError as e:
                trace.append({"type": "tool_error", "name": "lookup_patient", "error": e.code})
        
        # A2. Validate Beneficiary if any
        if state.resolved_patient_id and state.beneficiary_name and not state.beneficiary_verified:
            caller = store.get_patient(state.resolved_patient_id)
            if caller:
                b_name_lower = state.beneficiary_name.lower()
                b_id = None
                for child_id in caller.get("guardian_of", []):
                    child = store.get_patient(child_id)
                    if child and b_name_lower in child["name"].lower():
                        b_id = child_id
                        break
                if b_id:
                    state.resolved_patient_id = b_id
                    state.beneficiary_verified = True
                else:
                    state.escalation_reason = "not_authorised"
                    reply_text = replies.handoff_not_authorised()
                    # Cannot break from outer loop, so we continue to next turn checks but set escalation
                    pass
        
        # Target Appointment Resolution (for cancel/reschedule)
        if state.intent in ("cancel", "reschedule") and state.resolved_patient_id and not state.target_appointment_id and not state.escalation_reason:
            apts = store.list_appointments(state.resolved_patient_id)
            guard.add_list_appointments_result(apts)
            
            # Only consider booked appointments
            active_apts = [a for a in apts if a["status"] == "booked"]
            
            if state.intent == "cancel":
                # For cancel, extracted date/doctor refer to the existing appointment
                if state.date_iso:
                    active_apts = [a for a in active_apts if a["date"] == state.date_iso]
                if state.doctor:
                    active_apts = [a for a in active_apts if a["doctor_id"] == state.doctor]
            elif state.intent == "reschedule":
                # For reschedule, doctor might refer to existing appointment if not changing
                if state.doctor:
                    # Only filter if it matches one, else assume they are changing doctors
                    doc_apts = [a for a in active_apts if a["doctor_id"] == state.doctor]
                    if doc_apts:
                        active_apts = doc_apts

            if len(active_apts) == 1:
                state.target_appointment_id = active_apts[0]["id"]
                # Inherit doctor for reschedule if not specified
                if state.intent == "reschedule" and not state.doctor:
                    state.doctor = active_apts[0]["doctor_id"]
            elif len(active_apts) > 1:
                state.escalation_reason = "ambiguous_patient"
                reply_text = replies.handoff_ambiguous()
                break
            else:
                state.abandoned_reason = "no_appointment"
                reply_text = replies.abandoned_no_slots() # Reusing for "no appointment found"
                state.is_refused = False
                break

        # B. Search Slots
        if state.doctor and state.date_iso and state.intent in ("book", "reschedule") and not state.escalation_reason:
            # Prevent duplicate search if we just searched the exact same thing
            search_key = f"{state.doctor}_{state.date_iso}_{state.period}"
            if state.last_search_key != search_key:
                try:
                    tc = ToolCallRecord(name="search_slots", arguments={
                        "doctor_id": state.doctor, "date": state.date_iso, "period": state.period
                    })
                    # Remove None values
                    tc.arguments = {k: v for k, v in tc.arguments.items() if v is not None}
                    try:
                        SearchSlotsArgs(**tc.arguments)
                    except ValidationError as e:
                        raise ToolError("VALIDATION_ERROR", str(e))
                    tool_calls.append(tc)
                    
                    res = store.search_slots(state.doctor, state.date_iso, request.today, state.period)
                    guard.add_tool_result("search_slots", res)
                    trace.append({"type": "tool", "name": "search_slots", "args": tc.arguments, "result": res})
                    
                    state.last_search_result = res
                    state.last_search_key = search_key
                    
                    # Check reason
                    if res["reason"] == "HOLIDAY" or res["reason"] == "NOT_A_WORKING_DAY":
                        reply_text = replies.closed_day(state.date_iso)
                    elif res["reason"] == "DOCTOR_ON_LEAVE":
                        doc = store.get_doctor(state.doctor)
                        reply_text = replies.doctor_on_leave(state.date_iso, doc["name"] if doc else state.doctor)
                    elif not res["slots"]:
                        reply_text = replies.slot_taken_alternatives(state.time_hhmm or "yeh", state.date_iso, [])
                    else:
                        reply_text = replies.slots_offered(state.date_iso, state.doctor, res["slots"])
                        
                except ToolError as e:
                    trace.append({"type": "tool_error", "name": "search_slots", "error": e.code})
                
        # C. Mutation (Book / Reschedule / Cancel)
        # Only if no escalation/refusal is pending
        if not state.escalation_reason and not state.is_refused and not state.abandoned_reason:
            
            # BOOK
            if state.intent == "book" and state.resolved_patient_id and state.last_search_result and state.last_search_result["slots"]:
                # Chosen slot rule
                chosen_slot = None
                if state.time_hhmm and state.time_hhmm in state.last_search_result["slots"]:
                    chosen_slot = state.time_hhmm
                elif not state.time_hhmm:
                    # Pick earliest
                    chosen_slot = state.last_search_result["slots"][0]
                    
                if chosen_slot:
                    args = {
                        "patient_id": state.resolved_patient_id,
                        "doctor_id": state.doctor,
                        "date": state.date_iso,
                        "start": chosen_slot
                    }
                    if guard.check_mutation("book_appointment", args):
                        try:
                            BookAppointmentArgs(**args)
                        except ValidationError as e:
                            raise ToolError("VALIDATION_ERROR", str(e))
                        try:
                            tc = ToolCallRecord(name="book_appointment", arguments=args)
                            tool_calls.append(tc)
                            
                            res = store.book_appointment(**args, today=request.today)
                            guard.add_tool_result("book_appointment", res)
                            trace.append({"type": "tool", "name": "book_appointment", "args": tc.arguments, "result": res})
                            
                            state.successful_mutation = "booked"
                            state.mutated_appointment_id = res["id"]
                            state.mutated_patient_id = res["patient_id"]
                            
                            doc = store.get_doctor(state.doctor)
                            reply_text = replies.booked(state.date_iso, chosen_slot, doc["name"] if doc else state.doctor)
                            break # Mutation complete
                            
                        except ToolError as e:
                            trace.append({"type": "tool_error", "name": "book_appointment", "error": e.code})
                            if e.code == "SLOT_TAKEN":
                                reply_text = replies.slot_taken_alternatives(chosen_slot, state.date_iso, state.last_search_result["slots"])
                                
            # RESCHEDULE
            elif state.intent == "reschedule" and state.target_appointment_id and state.last_search_result and state.last_search_result["slots"]:
                chosen_slot = None
                if state.time_hhmm and state.time_hhmm in state.last_search_result["slots"]:
                    chosen_slot = state.time_hhmm
                elif not state.time_hhmm:
                    chosen_slot = state.last_search_result["slots"][0]
                    
                if chosen_slot:
                    args = {
                        "appointment_id": state.target_appointment_id,
                        "new_date": state.date_iso,
                        "new_start": chosen_slot
                    }
                    if guard.check_mutation("reschedule_appointment", args):
                        try:
                            RescheduleAppointmentArgs(**args)
                        except ValidationError as e:
                            raise ToolError("VALIDATION_ERROR", str(e))
                        try:
                            tc = ToolCallRecord(name="reschedule_appointment", arguments=args)
                            tool_calls.append(tc)
                            
                            res = store.reschedule_appointment(**args, today=request.today)
                            guard.add_tool_result("reschedule_appointment", res)
                            trace.append({"type": "tool", "name": "reschedule_appointment", "args": tc.arguments, "result": res})
                            
                            state.successful_mutation = "rescheduled"
                            state.mutated_appointment_id = res["id"]
                            state.mutated_patient_id = res["patient_id"]
                            
                            doc = store.get_doctor(state.doctor)
                            reply_text = replies.rescheduled(state.date_iso, chosen_slot, doc["name"] if doc else state.doctor)
                            break
                        except ToolError as e:
                            trace.append({"type": "tool_error", "name": "reschedule_appointment", "error": e.code})
                            
            # CANCEL
            elif state.intent == "cancel" and state.target_appointment_id:
                args = {"appointment_id": state.target_appointment_id}
                if guard.check_mutation("cancel_appointment", args):
                    try:
                        CancelAppointmentArgs(**args)
                    except ValidationError as e:
                        raise ToolError("VALIDATION_ERROR", str(e))
                    try:
                        tc = ToolCallRecord(name="cancel_appointment", arguments=args)
                        tool_calls.append(tc)
                        
                        res = store.cancel_appointment(**args)
                        guard.add_tool_result("cancel_appointment", res)
                        trace.append({"type": "tool", "name": "cancel_appointment", "args": tc.arguments, "result": res})
                        
                        state.successful_mutation = "cancelled"
                        state.mutated_appointment_id = res["id"]
                        state.mutated_patient_id = res["patient_id"]
                        
                        reply_text = replies.cancelled()
                        break
                    except ToolError as e:
                        trace.append({"type": "tool_error", "name": "cancel_appointment", "error": e.code})

        history.append(f"Caller: {text}")
        history.append(f"Agent: {reply_text}")

    # --- End of Turn Loop Checks ---
    if not state.resolved_patient_id and not state.escalation_reason and not state.is_refused and not state.abandoned_reason:
        if state.caller_name or state.caller_phone:
            res = store.lookup_patient(state.caller_name, state.caller_phone)
            if res["match"] == "multiple":
                state.escalation_reason = "ambiguous_patient"
                reply_text = replies.handoff_ambiguous()
            elif res["match"] == "none" and state.caller_name and state.caller_phone:
                state.escalation_reason = "not_authorised"
                reply_text = replies.handoff_not_authorised()

    # --- 4. POST-PROCESSING (Escalation Tool) ---
    if state.escalation_reason:
        try:
            tc = ToolCallRecord(name="escalate_to_human", arguments={
                "reason": state.escalation_reason,
                "detail": "Escalated by orchestrator",
                "patient_id": state.resolved_patient_id
            })
            # Remove None values
            tc.arguments = {k: v for k, v in tc.arguments.items() if v is not None}
            try:
                EscalateToHumanArgs(**tc.arguments)
            except ValidationError as e:
                raise ToolError("VALIDATION_ERROR", str(e))
            tool_calls.append(tc)
            
            res = store.escalate_to_human(**tc.arguments)
            trace.append({"type": "tool", "name": "escalate_to_human", "args": tc.arguments, "result": res})
            
            # Ensure reply matches escalation
            if state.escalation_reason == "clinical_urgent":
                reply_text = replies.handoff_clinical()
            elif state.escalation_reason == "not_authorised":
                reply_text = replies.handoff_not_authorised()
            # Others already set during loop
            
        except ToolError:
            pass

    # --- 5. TERMINAL STATE ---
    term_state, term_reason = determine_outcome(
        state.is_refused,
        state.escalation_reason,
        state.successful_mutation,
        bool(state.resolved_patient_id),
        state.intent
    )

    # --- 6. GUARD REPLY ---
    if not guard.check_reply(reply_text):
        reply_text = "Ji, ek minute..." # Safe fallback if hallucinated

    trace.append({
        "type": "agent",
        "text": reply_text
    })

    response = AgentResponse(
        conversation_id=request.conversation_id,
        tool_calls=tool_calls,
        terminal_state=term_state,
        escalation_reason=term_reason,
        patient_id=state.mutated_patient_id or state.resolved_patient_id,
        appointment_id=state.mutated_appointment_id,
        reply=reply_text,
    )
    response.metrics.turns = len(request.turns)
    response.metrics.tokens = total_tokens
    response.metrics.latency_ms = total_latency

    # Attach guard hits to trace
    trace.append({"type": "meta", "guard_hits": guard.hits})

    return response, trace
