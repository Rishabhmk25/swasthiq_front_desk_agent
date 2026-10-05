"""Safety layer: red flags, medical advice, injection detection, out-of-scope.

Precedence: injection/refusal > clinical_urgent > medical_advice > ordinary flow.
But clinical_urgent beats everything.
"""
from __future__ import annotations

import re

def near(w1: str, w2: str, dist: int = 6) -> str:
    """Helper to match w1 and w2 within `dist` words of each other in any order."""
    gap = f"(?:\\W+\\S+){{0,{dist}}}?\\W+"
    return f"(?:(?:{w1}){gap}(?:{w2})|(?:{w2}){gap}(?:{w1}))"

RED_FLAGS_REGEX = [
    r"heart\s+attack",
    near(r"\bseen\w*|\bsin[ae]\b|\bsine\b|\bsina\b|\bchh?a+ti\b|\bchest\b|\bheart\b|\bdil\b|सीने|छाती|दिल", r"\bdard\b|\bpain\b|\bjakdan\b|\btight\S*|\bpressure\b|\bbhaari\b|\bdabav\b|दर्द"),
    r"can'?t\s+breathe", r"cannot\s+breathe", r"not\s+breathing",
    near(r"\bbreath\S*|\bsaans\b|साँस|सांस", r"\bdifficul\S*|\bphool\S*|\btakleef\b|\bdikkat\b|\bnahi\s+aa\b|\bruk\b|फूल\S*|तकलीफ|दिक्कत"),
    r"\bfaint\S*|\bunconscious\S*|\bpass(?:ed)?\s+out|\bcollaps\S*|\bbehosh\b|गिर\s+गया|बेहोश",
    near(r"\bbleed\S*|\bkhoon\b|\bblood\b|खून", r"\bsever\S*|\bheavy\b|\bbahut\b|\bbeh\S*|\bjyada\b|\ba+\s+rahi\b|\baa\s+raha\b|बहुत|बह\s+रहा"),
    r"\bseizure\b|\bconvulsion\b|\bdaura\b|\bfits\b|दौरा",
    r"\bstroke\b|\bface\s+droop\S*|\bslurred\s+speech|\bone-sided\s+weakness|\bhaath\s+pair\s+sunn\b|\bhaath\s+sunn\b|\bek\s+taraf\b|\bsunn\s+pad\b|लकवा|हाथ\s+पैर\s+सुन्न",
    r"\bsuicid\S*|\bkill\s+myself|\bself\s*harm|\bmarna\s+chah\S*|\bjaan\s+dena|\bjeena\s+nahi\b|\bjee\s+nahi\b|\bkhatam\s+kar\b|\bapni\s+jaan\b|\blife\s+khatam\b|मरना\s+चाह|जान\s+देना",
    r"\bpoison\b|\boverdose\b|\bzeher\b|\bzehar\b|\bsnake\s*bite\b|\bsaanp\b|ज़हर|सांप",
    r"anaphylax\S*",
    near(r"swell\S*|sujh|sujhan|सूजन", r"lip|throat|gala|hont|गला|होंठ"),
    near(r"baby|infant|bachch[ea]|बच्च[ाे]", r"limp|not\s+feed\S*|doodh\s+nahi|high\s+fever|tez\s+bukhar|तेज़\s+बुखार|hil\s+nahi|hosh\s+nahi|uth\s+nahi"),
    near(r"head|sar|sir|सिर|सर", r"injur\S*|chot|चोट|severe"),
    # Pregnancy emergency
    r"(?:pregnan\S*|garbh|pet|पेट|गर्भ).{0,40}?(?:bleed\S*|khoon|bahut\s+dard|खून)",
    r"(?:bleed\S*|khoon|bahut\s+dard|खून).{0,40}?(?:pregnan\S*|garbh|pet|पेट|गर्भ)",
    r"(?:abhi|ho\s+gaya|ho\s+raha|just|right\s+now).{0,30}?(?:\baccident\b)",
    r"(?:\baccident\b).{0,30}?(?:abhi|ho\s+gaya|ho\s+raha|just|right\s+now)",
    r"\bemergency\b",
    r"\bambulance\b",
    r"\bbahut\s+chot\b|\bsevere\s+pain\b|\bterrible\s+pain\b"
]

MEDICAL_ADVICE_PATTERNS = [
    r"(?:kya\s+daw|kaun\s+si\s+daw|konsi\s+daw|which\s+med|what\s+med)",
    r"(?:should\s+i|can\s+i|kya\s+main).*(?:take|eat|kha|dose|pill)",
    r"(?:dawai?|goli|crocin|brufen|pill)\s+(?:lu|lun|kha|khaun|de\s+sakta|le\s+sakta)",
    r"(?:crocin|brufen|dawai|goli).*(?:lu|lun|kha|de\s+sakta|le\s+sakta)",
    r"kitni\s+dose",
    r"(?:kya|is)\s+(?:ye|it|this)\s+(?:serious|khatarnak|dangerous)",
    r"report\s+(?:kya\s+keh|padh|kaisa|normal|explain|samjha)",
    r"side\s+effect", r"interaction\b", r"reaction\s+to",
    r"(?:kab\s+tak|kitne\s+din\s+mein)\s+(?:theek|thik|better)",
    r"(?:what\s+is|kya\s+hai)\s+(?:the\s+)?(?:diagnosis|bimari)"
]

INJECTION_PATTERNS = [
    r"ignore\s+(?:your\s+)?(?:previous\s+)?instructions",
    r"administrator\s+mode",
    r"system\s*:", r"you\s+are\s+now",
    r"authorised\s+internal\s+test",
    r"authorized\s+internal\s+test",
    r"cancel\s+(?:every|all)",
    r"delete\s+all", r"remove\s+all",
    r"bulk\s+cancel", r"sab\s+cancel",
    r"saare?\s+appointment.*cancel",
    r"sabka?\s+cancel",
]

OUT_OF_SCOPE_PATTERNS = [
    # Only escalate if they strictly demand we give/send them a report/prescription now.
    r"(?:meri\s+)?prescription\s+(?:bhej|send|whatsapp|do\b)",
    r"(?:meri\s+)?report\s+(?:bhej|send|whatsapp|do\b)",
    r"(?:mera\s+)?refill\s+(?:kar\s+do|bhej|send|karo)"
]

def check_red_flags(text: str) -> dict:
    text_lower = text.lower()
    text_norm = re.sub(r'\b(mein|mai|men)\b', 'me', text_lower)
    
    for pattern in RED_FLAGS_REGEX:
        for match in re.finditer(pattern, text_norm, re.IGNORECASE):
            start, end = match.span()
            matched_text = match.group(0)
            
            if re.search(r'\b(no|not|nahi|nahin|bina|without)\b', matched_text, re.IGNORECASE):
                # Don't skip if the red flag pattern inherently has 'nahi' or 'not'
                if not re.search(r'(nahi\s+aa|not\s+breath|doodh\s+nahi|cannot|can\'?t|not\s+feed|jeena\s+nahi|jee\s+nahi|hil\s+nahi|hosh\s+nahi|uth\s+nahi)', matched_text, re.IGNORECASE):
                    continue
                
            prefix = text_norm[max(0, start-20):start]
            suffix = text_norm[end:min(len(text_norm), end+25)]
            
            negators = re.findall(r'\b(no|not|without|bina|nahi|nahin)\b', matched_text + " " + prefix + " " + suffix, re.IGNORECASE)
            if len(negators) >= 2 or re.search(r'(aisa nahi hai ki|not that)', prefix, re.IGNORECASE):
                return {"red_flag": True, "red_flag_phrase": matched_text}
                
            if re.search(r'\b(no|not|without|bina|nahi|nahin)(?:\s+\w+){0,2}\s+$', prefix, re.IGNORECASE):
                continue
                
            if re.search(r'^\s*(?:\w+\s+){0,2}(nahi|nahin|no\b|not\b)', suffix, re.IGNORECASE):
                continue
                
            return {"red_flag": True, "red_flag_phrase": matched_text}

    return {"red_flag": False, "red_flag_phrase": None}

def check_medical_advice(text: str) -> bool:
    text_lower = text.lower()
    for pattern in MEDICAL_ADVICE_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


def check_injection(text: str) -> bool:
    text_lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


def check_out_of_scope(text: str) -> bool:
    text_lower = text.lower()
    for pattern in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


def check_safety(text: str) -> dict:
    red = check_red_flags(text)
    return {
        "red_flag": red["red_flag"],
        "red_flag_phrase": red["red_flag_phrase"],
        "medical_advice": check_medical_advice(text),
        "injection": check_injection(text),
        "out_of_scope": check_out_of_scope(text),
    }
