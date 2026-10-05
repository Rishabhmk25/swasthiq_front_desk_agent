# SwasthiQ Clinic Agent

A robust, deterministic front-desk agent for Sunrise Clinic, Dehradun.
Built with FastAPI, React, and Gemini.

## 1. Quick Start

Run the entire application (backend, frontend, UI seeding) with one command:
```bash
make run
```
This will:
- Set up a Python venv if missing
- Install all backend and frontend dependencies
- Start the FastAPI backend on `http://localhost:8000`
- Start the React frontend on `http://localhost:5173`

## 2. Environment Variables

Create a `.env` file in the root directory (see `.env.example`):
- `LLM_PROVIDER`: `none` (or `gemini` to run with LLM fallback; `none` uses purely deterministic NLU rules)
- `LLM_MODEL`: `gemini-2.5-flash` (Using flash because the task requires fast extraction and classification; reasoning capabilities are kept in the deterministic rule layer)
- `GEMINI_API_KEY`: Your Gemini API key

## 3. Architecture

This system uses a **deterministic rules spine**:
- All conversational flow, orchestration, dates, times, and tool-calling decisions are controlled by Python rules.
- The LLM is used **strictly as an extractor** (converting text into a structured JSON frame).
- All executing tools are strongly guarded: appointments are only mutated if the slot was previously verified as free in the current conversation, and IDs exist.
- Patient authorisation is handled via exact string lookups (names/phones).
- Replies are purely templated to prevent the LLM from inventing facts (hallucinations).

## 4. API Contracts

### POST /agent/run
Request body: `{ "conversation_id": "string", "today": "YYYY-MM-DD", "turns": ["turn1", "turn2"] }`
Response body: Matches `schema.md` perfectly (terminal_state, escalation_reason, tools, metrics).

### Available Tools
| Tool Name | Arguments | Error Codes |
| --------- | --------- | ----------- |
| search_slots | doctor_id, date, period | HOLIDAY, DOCTOR_ON_LEAVE, PAST_DATE |
| lookup_patient | name, phone, dob | N/A |
| book_appointment | patient_id, doctor_id, date, start | NOT_A_SLOT, SLOT_TAKEN, HOLIDAY |
| reschedule_appointment | appointment_id, new_date, new_start | SLOT_TAKEN, INVALID_APPOINTMENT |
| cancel_appointment | appointment_id | ALREADY_CANCELLED |
| escalate_to_human | reason, detail, patient_id | N/A |

### UI Read Endpoints
- `GET /stats`: Aggregated handoff counts and completion metrics.
- `GET /handoffs?status=open`: List of unresolved escalations.
- `POST /handoffs/{id}/resolve`: Mark an escalation as resolved.
- `GET /conversations/{id}`: Fetch full conversation transcript, tools, outcome, and determinism.

## 5. Metrics

| Extractor Method | `LLM_PROVIDER` | Average Tokens | Average Latency (ms) |
|------------------|----------------|----------------|----------------------|
| **RulesOnlyExtractor** | `none`   | 0              | ~2060 ms             |
| **GeminiExtractor**    | `gemini` | ~400           | ~4500 ms             |

*(Note: Tokens are 0 when running purely on deterministic rules with `LLM_PROVIDER=none`)*

## 6. How to Test and Grade

Run tests:
```bash
make test
```

Run determinism test (runs 3 times):
```bash
make determinism
```

Run grader (scores out of 15):
```bash
make grade
```

## 7. Deployment

**Backend (Render):**
Use the included `render.yaml`. The startup script automatically seeds the database so the UI is populated immediately.

**Frontend (Vercel):**
Connect the `frontend` folder to Vercel. Set the environment variable `VITE_API_URL` to your Render backend URL.

## 8. Known Limitations
- The system heavily relies on specific deterministic NLU regex for parsing Hindi/Hinglish times and intents. While robust for the given scripts and variations, unexpected phrasing might require expanding the regex library.
- The in-memory SQlite DB approach currently requires all state to be flushed and recreated from `clinic.json` per instance. For high traffic, we should use a persistent DB (Postgres/Redis) for real-time concurrency across requests.
