"""NLU rules: deterministic extraction of dates, times, phones, doctors, names, intents.

All functions take `today: date` as parameter. No LLM, no datetime.now().
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

from app.models import TurnFrame


# --- Weekday mappings (English + Hindi + Hinglish + Devanagari) ---

WEEKDAY_MAP: dict[str, int] = {
    # English
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
    # Hindi / Hinglish
    "somwar": 0, "somvaar": 0, "sombaar": 0,
    "mangalwar": 1, "mangalvaar": 1,
    "budhwar": 2, "budhvaar": 2, "buddhwar": 2,
    "guruwar": 3, "guruvaar": 3, "veerwar": 3, "veervaar": 3, "brihaspatiwar": 3,
    "shukrawar": 4, "shukravaar": 4,
    "shanivaar": 5, "shaniwar": 5, "shaniwaar": 5,
    "raviwar": 6, "ravivaar": 6, "itwaar": 6, "aitwar": 6,
    # Short Hindi
    "somvar": 0, "mangalvar": 1, "budhvar": 2, "guruvar": 3,
    "shukravar": 4, "shanivar": 5, "ravivar": 6,
    # Devanagari
    "सोमवार": 0, "मंगलवार": 1, "बुधवार": 2, "गुरुवार": 3,
    "शुक्रवार": 4, "शनिवार": 5, "रविवार": 6,
}

# Correction markers - these signal the speaker is changing their mind
CORRECTION_MARKERS = [
    "nahi nahi", "nahi", "matlab", "i mean", "sorry", "actually",
    "rather", "ya phir", "baad mein sochte hain", "wait", "ruko",
    "nah", "are nahi", "nahin"
]

# Doctor mappings
DOCTOR_MAP: dict[str, str] = {
    "rao": "dr_rao", "anjali": "dr_rao", "dr. rao": "dr_rao", "dr rao": "dr_rao",
    "dr.rao": "dr_rao", "dr anjali rao": "dr_rao", "anjali rao": "dr_rao",
    "sethi": "dr_sethi", "vikram": "dr_sethi", "dr. sethi": "dr_sethi", "dr sethi": "dr_sethi",
    "dr.sethi": "dr_sethi", "dr vikram sethi": "dr_sethi", "vikram sethi": "dr_sethi",
    "paediatrician": "dr_sethi", "pediatrician": "dr_sethi",
    "bachche ke doctor": "dr_sethi", "bachche ka doctor": "dr_sethi",
    "bachchon ke doctor": "dr_sethi", "bachchon ka doctor": "dr_sethi",
}

# Period keywords
PERIOD_MAP: dict[str, str] = {
    "subah": "morning", "morning": "morning", "savere": "morning",
    "dopahar": "afternoon", "afternoon": "afternoon", "din mein": "afternoon",
    "shaam": "evening", "evening": "evening", "raat": "evening",
}

# Hindi number words
HINDI_NUMBERS: dict[str, int] = {
    "ek": 1, "do": 2, "teen": 3, "chaar": 4, "paanch": 5,
    "chhe": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
    "gyarah": 11, "baarah": 12, "terah": 13, "chaudah": 14, "pandrah": 15,
    "solah": 16, "satrah": 17, "attharah": 18, "unnis": 19, "bees": 20,
    "ikkees": 21, "baees": 22, "tees": 30, "ikatees": 31,
}

# Devanagari digits
DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# Intent keywords
BOOK_KEYWORDS = [
    "appointment chahiye", "milna hai", "dikhana hai", "book", "appointment karwana",
    "appointment lena", "dikha dijiye", "appointment karna", "milna tha",
    "appointment chahiye tha", "aa sakta", "aa sakti", "aa sakte",
]
RESCHEDULE_KEYWORDS = [
    "badalna", "change", "shift", "reschedule", "badal dijiye",
    "hatana", "aage badhana", "peeche karna",
]
CANCEL_KEYWORDS = [
    "cancel", "radd", "karna hai cancel", "cancel karna", "cancel karwa", "band",
]

# Relation keywords
RELATION_MAP: dict[str, str] = {
    "beta": "son", "bete": "son", "beti": "daughter", "bachcha": "child",
    "bachche": "child", "son": "son", "daughter": "daughter", "child": "child",
    "maa": "mother", "papa": "father", "wife": "wife", "husband": "husband",
    "padosi": "neighbour", "padosan": "neighbour", "neighbour": "neighbour",
    "neighbor": "neighbour", "friend": "friend", "dost": "friend",
}


def _devanagari_to_ascii(text: str) -> str:
    """Convert Devanagari digits to ASCII."""
    return text.translate(DEVANAGARI_DIGITS)


def _apply_corrections(text: str, field: str = "all") -> str:
    """Handle mid-sentence corrections: return text after the LAST correction marker."""
    text_lower = text.lower()
    last_pos = -1
    last_marker = ""
    for marker in CORRECTION_MARKERS:
        pos = text_lower.rfind(marker)
        if pos > last_pos:
            last_pos = pos
            last_marker = marker
    if last_pos >= 0:
        return text[last_pos + len(last_marker):].strip()
    return text


def extract_date(text: str, today: date) -> tuple[Optional[str], Optional[str]]:
    """Extract date from text. Returns (raw_phrase, iso_date) or (None, None)."""
    text_lower = _devanagari_to_ascii(text.lower().strip())

    # Handle corrections for dates
    corrected = _apply_corrections(text, "date")
    if corrected != text:
        text_lower = _devanagari_to_ascii(corrected.lower().strip())

    matches = []

    # Today / aaj
    for m in re.finditer(r'\b(today|aaj)\b', text_lower):
        matches.append((m.end(), "aaj", today.isoformat()))

    # Kal (tomorrow)
    for m in re.finditer(r'\bkal\b', text_lower):
        matches.append((m.end(), "kal", (today + timedelta(days=1)).isoformat()))

    # Parso (day after tomorrow)
    for m in re.finditer(r'\bparso\b', text_lower):
        matches.append((m.end(), "parso", (today + timedelta(days=2)).isoformat()))

    # Month parsing
    month_map = {
        "january": 1, "jan": 1, "february": 2, "feb": 2,
        "march": 3, "mar": 3, "april": 4, "apr": 4,
        "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
        "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10, "november": 11, "nov": 11,
        "december": 12, "dec": 12
    }
    
    date_pattern = r'\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:tareekh|tarik|tarikh|ko|of)?\s*(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sep|sept|october|oct|november|nov|december|dec)?\b'
    date_pattern_rev = r'\b(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sep|sept|october|oct|november|nov|december|dec)\s+(\d{1,2})(?:st|nd|rd|th)?\b'
    
    for m in re.finditer(date_pattern, text_lower):
        day_num = int(m.group(1))
        month_str = m.group(2)
        if 1 <= day_num <= 31:
            try:
                if month_str:
                    m_num = month_map[month_str]
                    d = date(today.year, m_num, day_num)
                    matches.append((m.end(), f"{day_num} {month_str}", d.isoformat()))
                else:
                    d = date(today.year, today.month, day_num)
                    if d < today:
                        # Roll forward to next month
                        next_month = (today.month % 12) + 1
                        next_year = today.year + (1 if today.month == 12 else 0)
                        d = date(next_year, next_month, day_num)
                    matches.append((m.end(), f"{day_num} tareekh", d.isoformat()))
            except ValueError:
                pass
                
    for m in re.finditer(date_pattern_rev, text_lower):
        month_str = m.group(1)
        day_num = int(m.group(2))
        if 1 <= day_num <= 31:
            try:
                m_num = month_map[month_str]
                d = date(today.year, m_num, day_num)
                matches.append((m.end(), f"{month_str} {day_num}", d.isoformat()))
            except ValueError:
                pass

    # Weekday names
    for name, weekday_num in WEEKDAY_MAP.items():
        pattern = r'\b' + re.escape(name) + r'\b'
        for m in re.finditer(pattern, text_lower, re.IGNORECASE):
            days_ahead = (weekday_num - today.weekday()) % 7
            if days_ahead == 0:
                if re.search(r'\bagle?\b', text_lower):
                    days_ahead = 7
            target = today + timedelta(days=days_ahead)
            
            # Check if a date number is also present closely
            num_match = re.search(r'(\d{1,2})\s*(?:tareekh|tarik|tarikh|ko)', text_lower)
            if num_match:
                day_num = int(num_match.group(1))
                try:
                    target = date(today.year, today.month, day_num)
                    matches.append((max(m.end(), num_match.end()), f"{name} {day_num} tareekh", target.isoformat()))
                    continue
                except ValueError:
                    pass
            matches.append((m.end(), name, target.isoformat()))

    # ISO date
    for m in re.finditer(r'(\d{4}-\d{2}-\d{2})', text_lower):
        matches.append((m.end(), m.group(1), m.group(1)))

    if matches:
        matches.sort(key=lambda x: x[0])
        return matches[-1][1], matches[-1][2]

    return (None, None)


def extract_time(text: str) -> tuple[Optional[str], Optional[str]]:
    """Extract time from text. Returns (raw_phrase, HH:MM) or (None, None)."""
    text_lower = _devanagari_to_ascii(text.lower().strip())

    # Handle corrections for time
    corrected = _apply_corrections(text, "time")
    if corrected != text:
        text_lower = _devanagari_to_ascii(corrected.lower().strip())

    # Hindi fractional times - check these FIRST before simple number matching
    # "dedh baje" = 1:30
    if re.search(r'\bdedh\s*baj', text_lower):
        return ("dedh baje", "13:30")  # Default PM for dedh
    # "dhai baje" = 2:30
    if re.search(r'\bdhai\s*baj', text_lower):
        return ("dhai baje", "14:30")
    # "saade X" / "sade X" = X:30
    saade_match = re.search(r'\bsaa?de\s+(\w+)', text_lower)
    if saade_match:
        num_word = saade_match.group(1)
        hour = HINDI_NUMBERS.get(num_word)
        if hour is None:
            try:
                hour = int(num_word)
            except ValueError:
                hour = None
        if hour is not None:
            if hour <= 6:
                hour += 12  # Assume PM for small numbers
            return (f"saade {num_word}", f"{hour:02d}:30")
    # "sawa X" = X:15
    sawa_match = re.search(r'\bsawa\s+(\w+)', text_lower)
    if sawa_match:
        num_word = sawa_match.group(1)
        hour = HINDI_NUMBERS.get(num_word)
        if hour is None:
            try:
                hour = int(num_word)
            except ValueError:
                hour = None
        if hour is not None:
            if hour <= 6:
                hour += 12
            return (f"sawa {num_word}", f"{hour:02d}:15")
    # "paune X" = (X-1):45
    paune_match = re.search(r'\bpaune\s+(\w+)', text_lower)
    if paune_match:
        num_word = paune_match.group(1)
        hour = HINDI_NUMBERS.get(num_word)
        if hour is None:
            try:
                hour = int(num_word)
            except ValueError:
                hour = None
        if hour is not None:
            actual_hour = hour - 1
            if actual_hour <= 6:
                actual_hour += 12
            return (f"paune {num_word}", f"{actual_hour:02d}:45")

    # 24h / 12h time: "10:30", "10.30", "3 pm", "3pm"
    time_match = re.search(r'(\d{1,2})[:\.](\d{2})\s*(am|pm)?', text_lower)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        ampm = time_match.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        return (time_match.group(0), f"{hour:02d}:{minute:02d}")

    # "X baje" pattern (Hindi "at X o'clock")
    baje_match = re.search(r'\b([a-zA-Z]+)\s*baj[e|a]?', text_lower)
    if baje_match:
        num_word = baje_match.group(1)
        hour = HINDI_NUMBERS.get(num_word)
        if hour is None:
            try:
                hour = int(num_word)
            except ValueError:
                hour = None
        if hour is not None:
            # Determine AM/PM from context
            if re.search(r'\b(subah|morning|savere)\b', text_lower):
                pass  # AM
            elif re.search(r'\b(shaam|evening|raat|dopahar)\b', text_lower):
                if hour < 12:
                    hour += 12
            elif hour <= 6:
                # Ambiguous small numbers, assume PM
                hour += 12
            return (f"{num_word} baje", f"{hour:02d}:00")

    # Simple "N pm" / "N am"
    simple_ampm = re.search(r'(\d{1,2})\s*(am|pm)', text_lower)
    if simple_ampm:
        hour = int(simple_ampm.group(1))
        ampm = simple_ampm.group(2)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        return (simple_ampm.group(0), f"{hour:02d}:00")

    # Bare number + "baje" in Hindi for time
    bare_time = re.search(r'\b(\d{1,2})\s*baje\b', text_lower)
    if bare_time:
        hour = int(bare_time.group(1))
        if hour <= 6:
            hour += 12
        return (f"{hour} baje", f"{hour:02d}:00")

    return (None, None)


def extract_phone(text: str) -> Optional[str]:
    """Extract 10-digit Indian mobile, tolerating +91, spaces, dashes, Devanagari."""
    text = _devanagari_to_ascii(text)
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)]', '', text)
    # Find phone pattern
    match = re.search(r'(?:\+?91)?(\d{10})', cleaned)
    if match:
        return match.group(1)
    return None


def extract_doctor(text: str) -> Optional[str]:
    """Extract doctor reference. Last mention wins (correction logic)."""
    text_lower = text.lower()
    corrected = _apply_corrections(text, "doctor")
    if corrected != text:
        text_lower = corrected.lower()

    last_doc = None
    last_pos = -1

    for keyword, doc_id in DOCTOR_MAP.items():
        pos = text_lower.rfind(keyword)
        if pos >= 0 and pos > last_pos:
            last_pos = pos
            last_doc = doc_id

    return last_doc


def extract_period(text: str) -> Optional[str]:
    """Extract morning/afternoon/evening from text."""
    text_lower = text.lower()
    for keyword, period in PERIOD_MAP.items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
            return period
    return None


def extract_name(text: str) -> Optional[str]:
    """Extract person name from patterns like 'Main X', 'X bol raha hoon', 'mera naam X'."""
    text_stripped = text.strip()

    junk_words = {"phone", "number", "is", "hai", "mera", "meri", "sir", "madam"}
    
    name_match = re.search(r'(?:[mM]ain|[mM]era\s+naam|[mM]y\s+name\s+is|[iI]\s+am|[iI]\'m)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)', text_stripped)
    if name_match:
        nm = name_match.group(1).strip()
        if not any(j in nm.lower().split() for j in junk_words):
            return nm

    # Fallback to look for proper noun at the end of the sentence
    padosi = re.search(r'padosi\s+hoon,?\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)', text_stripped)
    if padosi:
        nm = padosi.group(1).strip()
        if not any(j in nm.lower().split() for j in junk_words):
            return nm

    # "X bol raha/rahi hoon" pattern
    bol_match = re.search(r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+bol\s+rah[ai]\s+h[ou]+n', text_stripped, re.IGNORECASE)
    if bol_match:
        nm = bol_match.group(1).strip()
        if not any(j in nm.lower().split() for j in junk_words):
            return nm

    # "X here" pattern
    here_match = re.search(r'([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+here\b', text_stripped, re.IGNORECASE)
    if here_match:
        nm = here_match.group(1).strip()
        if not any(j in nm.lower().split() for j in junk_words):
            return nm

    # "Bas X" (Just X) pattern
    bas_match = re.search(r'\bbas\s+([a-zA-Z]+)\b', text_stripped, re.IGNORECASE)
    if bas_match:
        nm = bas_match.group(1).strip()
        if not any(j in nm.lower().split() for j in junk_words):
            return nm

    # Name + phone pattern: "Name, phone_number" or "Name phone_number"
    name_phone = re.search(r'^([a-zA-Z]+(?:\s+[a-zA-Z]+)*)[,\s]+(?:\+?91)?[\s\-]?\d{10}', text_stripped, re.IGNORECASE)
    if name_phone:
        nm = name_phone.group(1).strip()
        if not any(j in nm.lower().split() for j in junk_words):
            return nm

    return None


def extract_relation(text: str) -> tuple[Optional[str], Optional[str]]:
    """Extract relation and beneficiary name.
    Returns (relation, beneficiary_first_name) or (None, None).
    """
    text_lower = text.lower()

    # "mere/mera/meri beta/beti/bachcha X"
    for keyword, relation in RELATION_MAP.items():
        pattern = rf'(?:mer[aei]\s+|my\s+|for\s+my\s+){keyword}\s+([a-zA-Z]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            b_name = match.group(1).strip()
            if b_name.lower() != "hai":
                return (relation, b_name)

        # Without beneficiary name
        pattern2 = rf'(?:mer[aei]\s+|my\s+|for\s+my\s+){keyword}\b'
        if re.search(pattern2, text_lower):
            return (relation, None)

    # "X ke liye" / "X ko dikhana"
    for_match = re.search(r'\b([a-zA-Z]+)\s+(?:ke\s+liye|ko\s+(?:dikhana|milana|book))', text, re.IGNORECASE)
    if for_match:
        name = for_match.group(1).strip()
        stop_words = {"checkup", "bukhar", "khansi", "report", "follow", "followup", "test", "blood", "medicine", "dawai", "treatment", "vaccine", "check", "appointment", "check-up", "dr", "doctor", "benefits", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "aaj", "kal", "parso", "subah", "shaam", "raat", "dopehar", "baje", "claim"}
        if name.lower() not in DOCTOR_MAP and name.lower() not in stop_words:
            return (None, name)

    # "X ka/ki appointment"
    poss_match = re.search(r'\b([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)\s+(?:ka|ki|ke)\s+(?:aaj\s+ka\s+|kal\s+ka\s+|parso\s+ka\s+)?(?:appointment|booking)', text, re.IGNORECASE)
    if poss_match:
        name = poss_match.group(1).strip()
        months = {"january", "jan", "february", "feb", "march", "mar", "april", "apr", "may", "june", "jun", "july", "jul", "august", "aug", "september", "sep", "sept", "october", "oct", "november", "nov", "december", "dec"}
        ignore_words = {"dr", "doctor", "mera", "meri", "mere", "uska", "uski", "unka", "hamara", "hamari", "us", "aaj", "kal", "parson", "mera aaj", "mera kal"} | months
        if name.lower() not in DOCTOR_MAP and name.lower() not in ignore_words and not any(w in name.lower().split() for w in ["mera", "aaj", "kal"]):
            return (None, name)

    return (None, None)


def extract_intent(text: str) -> Optional[str]:
    """Extract intent cues from text."""
    text_lower = text.lower()

    # Check corrections first
    corrected = _apply_corrections(text, "intent")
    if corrected != text:
        text_lower = corrected.lower()

    for kw in CANCEL_KEYWORDS:
        if kw in text_lower:
            return "cancel"

    for kw in RESCHEDULE_KEYWORDS:
        if kw in text_lower:
            return "reschedule"

    for kw in BOOK_KEYWORDS:
        if kw in text_lower:
            return "book"

    # Implicit booking cues
    if "appointment hai" in text_lower and "chahiye" not in text_lower:
        # If they already have an appointment, and they are giving another date/time
        # It's likely a reschedule. "Mera appointment hai... use Saturday karwana hai"
        if "cancel" not in text_lower:
            return "reschedule"

    if re.search(r'\b(doctor|dr\.?)\b.*\b(saath|paas)\b', text_lower):
        if "appointment hai" not in text_lower:
            return "book"
    if re.search(r'\b(appointment|milna|dikhana)\b', text_lower):
        if "appointment hai" not in text_lower:
            return "book"

    return None


def is_noise(text: str) -> bool:
    """Check if a turn is just noise/filler with no usable content."""
    text_stripped = text.strip().lower()
    noise_patterns = [
        r'^hello\?*$', r'^haan\s*ji\.{0,3}$', r'^theek\s*hai\.{0,3}$',
        r'^ok\.{0,3}$', r'^accha\.{0,3}$', r'^hmm\.{0,3}$',
        r'^\[.*noise.*\]', r'^\.{1,3}$', r'^namaste\s*$',
        r'^haan\.{0,3}$', r'^ji\.{0,3}$',
        r'^arre\.{0,3}$',
    ]
    for pattern in noise_patterns:
        if re.search(pattern, text_stripped):
            return True
    # Very short generic turns
    if len(text_stripped) < 5 and not re.search(r'\d', text_stripped):
        return True
    return False


def analyse_turn(text: str, today: date) -> TurnFrame:
    """Analyse a single caller turn and return a structured TurnFrame.

    This is the main entry point for the deterministic NLU layer.
    """
    from app.agent.safety import check_safety  # Import here to avoid circular

    frame = TurnFrame()

    # Check for noise
    if is_noise(text):
        frame.noise = True
        return frame

    # Safety checks (red flags, medical advice, injection, out of scope)
    safety = check_safety(text)
    frame.red_flag = safety.get("red_flag", False)
    frame.red_flag_phrase = safety.get("red_flag_phrase")
    frame.medical_advice = safety.get("medical_advice", False)
    frame.injection = safety.get("injection", False)
    frame.out_of_scope = safety.get("out_of_scope", False)

    # Check for corrections
    text_lower = text.lower()
    for marker in CORRECTION_MARKERS:
        if marker in text_lower:
            frame.correction_seen = True
            break

    # Extract structured fields
    frame.doctor = extract_doctor(text)

    date_raw, date_iso = extract_date(text, today)
    frame.date_raw = date_raw
    frame.date_iso = date_iso

    time_raw, time_hhmm = extract_time(text)
    frame.time_raw = time_raw
    frame.time_hhmm = time_hhmm

    frame.period = extract_period(text)

    frame.phone = extract_phone(text)
    frame.patient_name = extract_name(text)

    relation, beneficiary = extract_relation(text)
    frame.relation = relation
    frame.beneficiary_name = beneficiary

    frame.intent = extract_intent(text)

    return frame
