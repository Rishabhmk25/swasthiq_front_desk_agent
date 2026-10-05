"""Hinglish reply templates.

Replies are constructed by filling these templates with tool results,
ensuring zero invented facts.
"""
from __future__ import annotations


def booked(date: str, time: str, doctor_name: str) -> str:
    return f"Ji, {date} ko {time} baje {doctor_name} ke saath appointment book ho gaya hai."

def rescheduled(date: str, time: str, doctor_name: str) -> str:
    return f"Ji, aapka appointment ab {date} ko {time} baje {doctor_name} ke saath reschedule ho gaya hai."

def cancelled() -> str:
    return "Ji, aapka appointment cancel kar diya gaya hai."

def slots_offered(date: str, doctor_name: str, slots: list[str]) -> str:
    if not slots:
        return closed_day(date)
    top = slots[:3]
    return f"{doctor_name} ke {date} ke liye ye samay uplabdh hain: {', '.join(top)}. Aapko kaunsa time theek rahega?"

def closed_day(date: str) -> str:
    return f"Maaf kijiye, {date} ko clinic band hai ya doctor us din nahi baithte."

def doctor_on_leave(date: str, doctor_name: str) -> str:
    return f"Maaf kijiye, {doctor_name} {date} ko chhutti par hain."

def slot_taken_alternatives(time: str, date: str, slots: list[str]) -> str:
    if not slots:
        return f"Maaf kijiye, {time} baje {date} ko slot full hai aur koi aur slot bhi free nahi hai."
    top = slots[:3]
    return f"Maaf kijiye, {time} baje {date} ko slot full hai. Lekin ye slots free hain: {', '.join(top)}."

def need_identity() -> str:
    return "Booking aage badhane ke liye kripya apna pura naam aur phone number bataiye."

def ambiguous_name() -> str:
    return "Is naam se kayi patients hain. Kripya apna phone number bataiye."

def ambiguous_phone() -> str:
    return "Is number par kayi patients hain. Kripya apna poora naam bataiye."

def handoff_clinical() -> str:
    return "Ye ek medical emergency lag rahi hai. Kripya turant nazdiki aspatal (hospital) jayen ya emergency number par call karein. Main is call ko aage transfer kar raha/rahi hoon."

def handoff_medical_advice() -> str:
    return "Main medical advice nahi de sakta. Main aapki baat ek human agent se karwa deta hoon."

def handoff_not_authorised() -> str:
    return "Maaf kijiye, main aapko is appointment ki jaankari ya badlav karne ki anumati nahi de sakta. Main call transfer kar raha hoon."

def handoff_ambiguous() -> str:
    return "Mujhe aapka record confirm karne mein pareshani ho rahi hai. Main aapko kisi aur se baat karwata hoon."

def handoff_out_of_scope() -> str:
    return "Main is vishay par madad nahi kar paunga. Main call human agent ko transfer kar raha hoon."

def refused() -> str:
    return "Maaf kijiye, main ye request poori nahi kar sakta."

def noop() -> str:
    return "Ji, aur kuch madad kar sakta hoon?"

def abandoned_no_slots() -> str:
    return "Maaf kijiye, us din koi slot free nahi hai."
def patient_not_found(name_or_phone: str | None) -> str:
    return f"Main {name_or_phone} naam se koi record nahi dhoondh paa raha."
