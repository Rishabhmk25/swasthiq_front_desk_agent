import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Optional, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import CLINIC_JSON, CORS_ORIGINS, LOGS_DB_PATH, LLM_PROVIDER
from app.models import AgentRequest, AgentResponse
from app.tools.store import ClinicStore
from app.agent.nlu_llm import GeminiExtractor, RulesOnlyExtractor
from app.agent.orchestrator import run_conversation


app = FastAPI(title="SwasthiQ Clinic Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # allow all for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = sqlite3.connect(LOGS_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@app.on_event("startup")
def startup_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            today TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            terminal_state TEXT,
            escalation_reason TEXT,
            patient_id TEXT,
            appointment_id TEXT,
            tool_names_json TEXT,
            tokens INTEGER,
            latency_ms INTEGER,
            turns INTEGER,
            llm_fallback BOOLEAN,
            guard_hits INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS run_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            seq INTEGER,
            kind TEXT,
            text TEXT,
            tool_name TEXT,
            tool_args_json TEXT,
            tool_result_summary TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS handoffs (
            conversation_id TEXT PRIMARY KEY,
            reason TEXT,
            caller_said TEXT,
            trigger_turn INTEGER,
            status TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            resolved_at DATETIME
        )
    """)
    
    # Seed data if empty
    count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    if count == 0:
        run_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO runs (id, conversation_id, today, terminal_state, escalation_reason, tool_names_json, tokens, latency_ms, turns, llm_fallback, guard_hits)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, "cv_demo_001", "2026-10-01", "escalated", "clinical_urgent", "[\"search_slots\"]", 0, 15, 3, False, 0)
        )
        conn.execute(
            """INSERT INTO handoffs (conversation_id, reason, caller_said, trigger_turn, status)
               VALUES (?, ?, ?, ?, 'open')""",
            ("cv_demo_001", "clinical_urgent", "Chest pain", 3)
        )
        conn.commit()

    conn.close()


@app.post("/agent/run", response_model=AgentResponse)
def run_agent(request: AgentRequest):
    """Run a full conversation in an isolated ClinicStore."""
    try:
        from datetime import date
        date.fromisoformat(request.today)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid today format")
        
    if len(request.turns) > 30:
        raise HTTPException(status_code=422, detail="Too many turns")
    if any(len(t) > 2000 for t in request.turns):
        raise HTTPException(status_code=422, detail="Turn too long")

    store = ClinicStore(CLINIC_JSON)
    if LLM_PROVIDER == "gemini":
        extractor = GeminiExtractor()
    else:
        extractor = RulesOnlyExtractor()
    
    start_time = datetime.now()
    try:
        response, trace = run_conversation(request, store, extractor)
    except Exception as e:
        print(f"Internal Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
        
    end_time = datetime.now()
    latency = int((end_time - start_time).total_seconds() * 1000)
    response.metrics.latency_ms = latency

    # Log to DB
    run_id = str(uuid.uuid4())
    try:
        conn = get_db()
        tool_names = [tc.name for tc in response.tool_calls]
        
        conn.execute(
            """INSERT INTO runs 
               (id, conversation_id, today, terminal_state, escalation_reason, patient_id, appointment_id, tool_names_json, tokens, latency_ms, turns, llm_fallback, guard_hits)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, request.conversation_id, request.today, response.terminal_state, response.escalation_reason, 
             response.patient_id, response.appointment_id, json.dumps(tool_names), response.metrics.tokens, latency, 
             len(request.turns), False, 0)
        )
        
        seq = 0
        trigger_turn = 0
        caller_said = ""
        for t in trace:
            if t["type"] == "meta": continue
            seq += 1
            kind = t["type"]
            text = t.get("text", "")
            tool_name = t.get("name", "")
            tool_args = json.dumps(t.get("args", {})) if "args" in t else None
            
            # Simple summary for tool
            summary = None
            if kind == "tool":
                res = t.get("result", {})
                if isinstance(res, dict) and "candidates" in res:
                    summary = f"{len(res['candidates'])} candidates"
                elif isinstance(res, dict) and "slots" in res:
                    slots_str = ", ".join(res["slots"])
                    summary = f"{len(res['slots'])} slots: {slots_str}"
                elif isinstance(res, dict) and "status" in res:
                    summary = res["status"]
                else:
                    summary = "success"

            conn.execute(
                "INSERT INTO run_events (run_id, seq, kind, text, tool_name, tool_args_json, tool_result_summary) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (run_id, seq, kind, text, tool_name, tool_args, summary)
            )
            
            if kind == "caller":
                caller_said = text
                trigger_turn += 1

        if response.terminal_state == "escalated":
            conn.execute(
                """INSERT OR REPLACE INTO handoffs (conversation_id, reason, caller_said, trigger_turn, status)
                   VALUES (?, ?, ?, ?, 'open')""",
                (request.conversation_id, response.escalation_reason, caller_said, trigger_turn)
            )
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging run: {e}")
        
    return response


@app.get("/stats")
def get_stats():
    conn = get_db()
    
    # Get distinct latest runs per conversation
    # A simple way is to use a subquery to get the latest run_id per conversation
    q = """
        SELECT r.* FROM runs r
        INNER JOIN (
            SELECT conversation_id, MAX(created_at) as max_dt 
            FROM runs GROUP BY conversation_id
        ) latest ON r.conversation_id = latest.conversation_id AND r.created_at = latest.max_dt
    """
    rows = conn.execute(q).fetchall()
    
    conversations = len(rows)
    completed = sum(1 for r in rows if r["terminal_state"] in ("booked", "rescheduled", "cancelled", "refused", "abandoned"))
    completed_pct = int(completed / conversations * 100) if conversations > 0 else 0
    escalated = sum(1 for r in rows if r["terminal_state"] == "escalated")
    
    handoff_rows = conn.execute("SELECT * FROM handoffs WHERE status='open'").fetchall()
    escalated_open = len(handoff_rows)
    urgent_unresolved = sum(1 for h in handoff_rows if h["reason"] == "clinical_urgent")
    
    conn.close()
    return {
        "conversations": conversations,
        "completed_by_agent": completed,
        "completed_pct": completed_pct,
        "escalated": escalated,
        "escalated_open": escalated_open,
        "urgent_unresolved": urgent_unresolved
    }


@app.get("/handoffs")
def get_handoffs(status: str = "open"):
    conn = get_db()
    rows = conn.execute("SELECT * FROM handoffs WHERE status=? ORDER BY created_at DESC", (status,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/handoffs/{conversation_id}/resolve")
def resolve_handoff(conversation_id: str):
    conn = get_db()
    conn.execute("UPDATE handoffs SET status='resolved', resolved_at=CURRENT_TIMESTAMP WHERE conversation_id=?", (conversation_id,))
    conn.commit()
    conn.close()
    return {"status": "resolved"}


@app.get("/conversations")
def list_conversations():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT conversation_id FROM runs ORDER BY conversation_id").fetchall()
    conn.close()
    return [{"id": r["conversation_id"]} for r in rows]


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    conn = get_db()
    # Get all runs for determinism
    runs = conn.execute("SELECT * FROM runs WHERE conversation_id=? ORDER BY created_at ASC", (conversation_id,)).fetchall()
    if not runs:
        conn.close()
        raise HTTPException(status_code=404, detail="Not found")
        
    latest_run = runs[-1]
    
    events = conn.execute("SELECT * FROM run_events WHERE run_id=? ORDER BY seq", (latest_run["id"],)).fetchall()
    
    # Determinism check
    # Check if terminal_state, escalation_reason, and tool_names_json are identical across all runs
    stable = True
    first_run = runs[0]
    first_sig = (first_run["terminal_state"], first_run["escalation_reason"], json.dumps(sorted(json.loads(first_run["tool_names_json"]))))
    
    for r in runs[1:]:
        sig = (r["terminal_state"], r["escalation_reason"], json.dumps(sorted(json.loads(r["tool_names_json"]))))
        if sig != first_sig:
            stable = False
            break
            
    header = f"Date: {latest_run['today']}"
    
    outcome = {
        "terminal_state": latest_run["terminal_state"],
        "escalation_reason": latest_run["escalation_reason"],
        "patient_id": latest_run["patient_id"],
        "appointment_id": latest_run["appointment_id"],
        "tool_calls": len(json.loads(latest_run["tool_names_json"])),
        "turns": latest_run["turns"],
        "tokens": latest_run["tokens"],
        "latency_ms": latest_run["latency_ms"]
    }
    
    banner = None
    if latest_run["terminal_state"] == "escalated" and "search_slots" in latest_run["tool_names_json"] and not latest_run["appointment_id"]:
        banner = "Booking flow abandoned. No appointment was created."
        
    ev_list = []
    for e in events:
        ev_list.append({
            "kind": e["kind"],
            "text": e["text"],
            "tool_name": e["tool_name"],
            "tool_args_json": e["tool_args_json"],
            "tool_result_summary": e["tool_result_summary"]
        })
        
    conn.close()
    
    return {
        "header": header,
        "outcome": outcome,
        "events": ev_list,
        "banner": banner,
        "determinism": {
            "runs": len(runs),
            "stable": stable,
            "fingerprints": []
        }
    }


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/patients")
def list_patients():
    with open(CLINIC_JSON, "r") as f:
        data = json.load(f)
    return data.get("patients", [])

@app.get("/appointments")
def list_appointments():
    with open(CLINIC_JSON, "r") as f:
        data = json.load(f)
    return data.get("appointments", [])

@app.get("/doctors")
def list_doctors():
    with open(CLINIC_JSON, "r") as f:
        data = json.load(f)
    return data.get("doctors", [])

