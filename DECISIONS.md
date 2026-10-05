# Architectural Decisions

## 1. Why deterministic NLU instead of Agentic LLM?
In healthcare operations, strict guardrails are paramount. An autonomous LLM agent that decides *when* to execute a tool (like `book_appointment`) is prone to hallucinations (e.g. hallucinating availability), prompt injections, or unpredictable pathing. By using an LLM **only** for structured extraction (as an NLU component parsing variables like date and intent) and managing the workflow with a deterministic Python state machine (`orchestrator.py`), we achieve 100% stable routing.

## 2. Pydantic Models for Tool Contracts
All external tool inputs are passed through strictly typed Pydantic models (e.g., `SearchSlotsArgs`, `BookAppointmentArgs`). This ensures that if the extraction phase passes an invalid date format or a malformed phone number, it gets instantly caught as a `ValidationError`, caught by the orchestrator, and converted into a benign `ToolError` before it reaches the core data store.

## 3. The Commit-Last Safety Architecture
Patient safety is handled via a **Pre-Scan Loop**. Before the orchestrator processes the state for booking or lookup, it loops over all conversation turns to evaluate regex-based stem matching for clinical urgency (e.g., "chest pain", "bleeding"). If an emergency is detected anywhere in the context window, the loop breaks instantly and calls `escalate_to_human("clinical_urgent")`. This guarantees that no administrative mutations (like booking) can execute in the same turn as an unhandled medical emergency.

## 4. Name/Phone Dual-Authentication
To prevent impersonation, the `lookup_patient` tool enforces an exact string match (case-insensitive) across *both* `name` and `phone` simultaneously. A naive system might lookup by phone, see a record, and assume the speaker is the owner even if the speaker provided a mismatched name. Here, mismatched credentials return `multiple` or empty matches, which triggers an `ambiguous_patient` escalation to human staff, preventing accidental data leaks.

## 5. In-Memory SQLite vs JSON
The `ClinicStore` uses an in-memory SQLite database initialized from `clinic.json`. This provides rich relational querying (like JOINs and aggregations) for the dashboard while ensuring each `/agent/run` invocation is fully stateless and isolated. A production implementation would simply replace the connection string with a persistent PostgreSQL instance.

## 6. Starter Pack Issues Identified
| Issue | Location | Resolution |
| ----- | -------- | ---------- |
| Beneficiary validation bypassed | `orchestrator.py` | The system initially checked for `beneficiary_name` (e.g. "for Aman") only when `lookup_patient` was triggered in that same turn. If the name was provided later, it bypassed the check. Extracted this validation check so it runs globally on every turn if `beneficiary_name` is present. |
| Incomplete test assertions | `test_agent_happy.py` | Missing coverage for turn loops and adversarial injections in early testing. Fixed by relying on the deterministic runner and standardising pytest suite. |
| Missing `date` vs `date_str` format | `schema.md` / `guard.py` | Schema stated `YYYY-MM-DD` but the grounding guard validated against a missing `date_str` argument causing a runtime exception. Fixed by aligning the guard argument to `date`. |
| Buggy orchestrator loop | orchestrator.py | Orchestrator loop was terminating early using break for patient lookup ambiguities, skipping missing information. Fixed by using else/continue blocks. |
| Multiple Beneficiary Checks | orchestrator.py | The beneficiary relationship validation was executing on every turn if a beneficiary was set, causing self-authorization checks and resulting in erroneous escalation. Fixed by introducing beneficiary_verified state flag. |
