"""Grade script: compares runner results to expected results in clinic.json."""
import json
import glob
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent.parent.parent
    results_dir = root / "results"
    convos_dir = root / "conversations"
    
    # Load all expected
    expected = {}
    for f in convos_dir.glob("cv_*.json"):
        with open(f, "r") as fp:
            data = json.load(fp)
            expected[data["id"]] = data["expected"]
            
    # Load results
    results_files = list(results_dir.glob("*.run1.json"))
    if not results_files:
        print("No results found. Run python runner.py first.")
        return
        
    print(f"Grading {len(results_files)} results")
    print("-" * 50)
    
    passed = 0
    total = len(results_files)
    failures = []
    
    for f in results_files:
        with open(f, "r") as fp:
            r = json.load(fp)
        cid = r["conversation_id"]
        exp = expected[cid]
        
        term = r["terminal_state"]
        esc = r["escalation_reason"]
        
        is_pass = True
        reasons = []
        
        if term != exp["terminal_state"]:
            is_pass = False
            reasons.append(f"State expected '{exp['terminal_state']}', got '{term}'")
            
        if esc != exp.get("escalation_reason"):
            is_pass = False
            reasons.append(f"Escalation expected '{exp.get('escalation_reason')}', got '{esc}'")
            
        # Check must_call / must_not_call
        called = [tc["name"] for tc in r.get("tool_calls", [])]
        
        for mc in exp.get("must_call", []):
            if mc not in called:
                is_pass = False
                reasons.append(f"Missing required tool: {mc}")
                
        for mnc in exp.get("must_not_call", []):
            if mnc in called:
                is_pass = False
                reasons.append(f"Forbidden tool called: {mnc}")
                
        if is_pass:
            passed += 1
            print(f"[PASS] {cid}")
        else:
            print(f"[FAIL] {cid}")
            for reason in reasons:
                print(f"   - {reason}")
            failures.append(cid)
            
    print("-" * 50)
    print(f"Score: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if failures:
        print("\nFailing conversations:")
        for f in failures:
            print(f"  {f}")
        exit(1)

if __name__ == "__main__":
    main()
