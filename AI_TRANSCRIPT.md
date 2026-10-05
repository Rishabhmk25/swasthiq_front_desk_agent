# AI Transcript

Below is a summary of the AI prompts used to generate the determinism testing scripts, adversarial edge cases, and UI scaffolding for this project.

## 1. Generating Adversarial Edge Cases
**Prompt:**
> Generate a JSON file containing a list of 6 adversarial test cases for a medical front desk agent. The agent should be tested against edge cases like prompt injections mixed with real medical emergencies, booking attempts that lack specific dates but contain month names, and sentences that use the word "report" or "medicine" in a benign context (e.g. "I want to show my report to the doctor"). Ensure the output matches this schema: `{"id": "...", "description": "...", "turns": [], "expected": {"terminal_state": "...", "escalation_reason": "...", "must_call": [], "must_not_call": [], "notes": "A naive agent might..."}}`.

**Result:**
The AI generated the structured adversarial cases found in `adversarial/`.

## 2. Pydantic Integration
**Prompt:**
> I have a legacy `store.py` with Python functions for `book_appointment`, `search_slots`, etc. Write Pydantic models for the arguments of these functions to enforce strict typing (e.g., ISO dates, specific string formats). Then show me how to safely `try/except` these models in my orchestrator before executing the underlying function, converting any `ValidationError` into a custom `ToolError`.

**Result:**
The AI provided `models.py` schemas which were manually integrated into `orchestrator.py`'s tool execution blocks.

## 3. UI Analytics Dashboard
**Prompt:**
> Write a React functional component using Vite/React Router that displays a "Handoff Queue". It should fetch from `/stats` and `/handoffs?status=open`. Use raw CSS (no Tailwind) to create a clean, modern grid layout with statistic cards (Conversations, Completed, Escalated, Urgent). Include a table that renders the open handoffs with a pill badge for the `reason`. Make sure it uses `created_at` for timestamps.

**Result:**
The AI generated the foundational JSX for `HandoffQueue.jsx` and `ConversationDetail.jsx`, which was then refined to match the project's CSS styling.
