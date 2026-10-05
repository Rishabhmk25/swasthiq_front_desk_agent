import json
import logging
from app.config import CLINIC_JSON
from app.tools.store import ClinicStore
from app.agent.nlu_llm import RulesOnlyExtractor
from app.agent.orchestrator import run_conversation
from app.models import AgentRequest

logging.basicConfig(level=logging.DEBUG)

def main():
    store = ClinicStore(CLINIC_JSON)
    extractor = RulesOnlyExtractor()
    
    with open("conversations/cv_0009.json") as f:
        data = json.load(f)
        
    req = AgentRequest(
        conversation_id=data["id"],
        today=data["today"],
        turns=data["turns"]
    )
    
    resp, trace = run_conversation(req, store, extractor)
    print("\n--- FINAL RESPONSE ---")
    print(resp.model_dump_json(indent=2))
    
if __name__ == "__main__":
    main()
