import pytest
import os
from datetime import date

from app.models import AgentRequest
from app.tools.store import ClinicStore
from app.agent.orchestrator import run_conversation
from app.agent.nlu_llm import RulesOnlyExtractor

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "clinic.json")


@pytest.fixture
def store():
    return ClinicStore(DATA_PATH)

@pytest.fixture
def extractor():
    return RulesOnlyExtractor()


def test_agent_book_happy(store, extractor):
    """Happy path booking."""
    req = AgentRequest(
        conversation_id="test_book",
        today="2026-10-01",
        turns=[
            "Dr. Rao ke saath kal ka appointment chahiye tha.",
            "Subah 10 baje.",
            "Rajesh Sharma, 9812200073"
        ]
    )
    
    resp, trace = run_conversation(req, store, extractor)
    assert resp.terminal_state == "booked"
    assert any(tc.name == "book_appointment" for tc in resp.tool_calls)
    assert resp.appointment_id is not None

def test_agent_reschedule_happy(store, extractor):
    """Happy path reschedule."""
    req = AgentRequest(
        conversation_id="test_reschedule",
        today="2026-10-01",
        turns=[
            "Mera naam Priya Nair hai, 9812200104",
            "Mera jo aaj ka appointment hai, usko parso subah kar do."
        ]
    )
    
    resp, trace = run_conversation(req, store, extractor)
    assert resp.terminal_state == "rescheduled"
    assert any(tc.name == "reschedule_appointment" for tc in resp.tool_calls)
    assert resp.appointment_id is not None


def test_agent_cancel_happy(store, extractor):
    """Happy path cancel."""
    req = AgentRequest(
        conversation_id="test_cancel",
        today="2026-10-01",
        turns=[
            "Rajesh Sharma, 9812200073",
            "Mujhe apna appointment cancel karna hai."
        ]
    )
    
    resp, trace = run_conversation(req, store, extractor)
    assert resp.terminal_state == "cancelled"
    assert any(tc.name == "cancel_appointment" for tc in resp.tool_calls)
    assert resp.appointment_id is not None
