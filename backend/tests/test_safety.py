import pytest
from app.agent.safety import check_safety

TEST_CASES = [
    # True positives (Chest pain)
    ("I have a sharp pain in my chest", True),
    ("seene mein bahut dard hai", True),
    ("chhati mein thoda dard ho raha hai", True),
    ("mujhe lagta hai heart attack hai", True),
    ("mujhe chest me dard ho raha hai", True),
    ("waise abhi seene me dard ho raha hai", True),
    ("dard ho raha hai seene mein", True), 
    ("छाती में दर्द", True),
    ("सीने में तेज़ दर्द है", True),
    
    # True positives (Breathlessness)
    ("saans lene mein dikkat", True),
    ("saans nahi aa rahi", True), 
    ("can't breathe", True),
    ("cannot breathe", True),
    
    # True positives (Fainting)
    ("my father just collapsed", True),
    ("wo behosh ho gaya", True),
    
    # True positives (Bleeding)
    ("bahut khoon aa raha hai", True),
    ("khoon beh raha hai", True),
    ("meri wife pregnant hai aur bleeding ho rahi hai", True),
    
    # True positives (Seizure / stroke)
    ("bete ko fits aa rahe hain", True),
    ("ek taraf ka haath kaam nahi kar raha", True),
    ("haath sunn pad gaya", True),
    
    # True positives (Baby/Child)
    ("baby limp", True),
    ("bachcha doodh nahi pee raha", True),
    
    # True positives (General emergency)
    ("accident ho gaya, bahut chot lagi", True),
    ("saanp ne kaata", True),
    ("ambulance chahiye", True),
    ("yeh emergency hai", True),
    ("suicide karna chahta", True),
    
    # Negations (Should NOT flag)
    ("dard nahi hai seene mein", False),
    ("no chest pain", False),
    ("chest pain nahi hai", False),
    ("chhati mein dard nahi tha", False),
    ("seene me koi dard nahi lag raha", False),
    ("I do not have chest pain", False),
    ("without chest pain", False),
    
    # False negatives check (Should STILL flag, negation is in another clause)
    ("mujhe bukhar hai par seene me dard nahi, wait seene me dard hai", True),
    ("pata nahi kya ho raha hai, chest pain hai", True),
    ("main kal nahi aa sakta, seene mein dard hai", True),
    
    # Not red flags (Should NOT flag)
    ("I need an appointment", False),
    ("mujhe kal aana hai", False),
    ("bukhar hai", False),
    ("kya medicine lu", False), 
]

@pytest.mark.parametrize("text, expected_flag", TEST_CASES)
def test_red_flags(text, expected_flag):
    result = check_safety(text)
    assert result["red_flag"] == expected_flag, f"Failed on: {text}"

def test_medical_advice():
    # Should flag
    assert check_safety("kya tab tak main bacche ko crocin de sakta hoon")["medical_advice"]
    assert check_safety("kya dawai lun")["medical_advice"]
    assert check_safety("report kya kehti hai")["medical_advice"]
    assert check_safety("is this serious")["medical_advice"]

    # Should NOT flag (Ordinary bookings)
    assert not check_safety("medicine lene ke liye appointment")["medical_advice"]
    assert not check_safety("treatment ke liye appointment")["medical_advice"]
    assert not check_safety("slot le sakta hoon?")["medical_advice"]
    assert not check_safety("report dikhane ke liye")["medical_advice"]

def test_out_of_scope():
    assert check_safety("meri prescription bhej do")["out_of_scope"]
    assert check_safety("report bhej do")["out_of_scope"]
    assert check_safety("refill kar do")["out_of_scope"]
    
    # These should NOT be out of scope
    assert not check_safety("fees kitni hogi")["out_of_scope"]
    assert not check_safety("report dikhane aana hai")["out_of_scope"]
    assert not check_safety("appointment book karna hai")["out_of_scope"]

