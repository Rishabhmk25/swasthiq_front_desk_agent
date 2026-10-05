import json
import glob
from app.models import AgentRequest
from app.agent.orchestrator import run_conversation
from app.tools.store import ClinicStore
from app.agent.nlu_llm import RulesOnlyExtractor

store = ClinicStore('app/data/clinic.json')
extractor = RulesOnlyExtractor()

for f in sorted(glob.glob('../adversarial/*.json')):
    with open(f) as handle:
        d = json.load(handle)
    req = AgentRequest(conversation_id=d['id'], today=d['today'], turns=d['turns'])
    res, _ = run_conversation(req, store, extractor)
    exp = d['expected']
    passed = True
    if res.terminal_state != exp['terminal_state']: passed = False
    if res.escalation_reason != exp.get('escalation_reason'): passed = False
    status = "PASS" if passed else "FAIL"
    print(f"{d['id']}: {status} (Expected {exp['terminal_state']}/{exp.get('escalation_reason')}, got {res.terminal_state}/{res.escalation_reason})")
