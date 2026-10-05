import sys
import logging
from app.config import CLINIC_JSON
from app.tools.store import ClinicStore
from app.agent.nlu_llm import RulesOnlyExtractor
from app.agent.orchestrator import run_conversation
from app.models import AgentRequest
import json
import os
import datetime

logging.basicConfig(level=logging.DEBUG)

def main():
    store = ClinicStore(CLINIC_JSON)
    extractor = RulesOnlyExtractor()
    
    with open(os.path.join("..", "conversations", "cv_0008.json")) as f:
        data = json.load(f)
        
    req = AgentRequest(
        conversation_id=data["id"],
        today=data["today"],
        turns=data["turns"]
    )
    
    for text in req.turns:
        print(f"Turn text: {text}")
        f = extractor.extract(text, [], datetime.date.fromisoformat(req.today))[0]
        print(f"Frame: {f}")
        print("-------")
        
    print("\n--- FINAL RESPONSE ---")
    resp, trace = run_conversation(req, store, extractor)
    print(resp.model_dump_json(indent=2))

if __name__ == "__main__":
    main()
