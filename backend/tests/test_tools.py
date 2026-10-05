import pytest
import os
import threading

from app.tools.store import ClinicStore
from app.errors import ToolError

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "clinic.json")


def test_race_condition():
    """20 threads book the same slot, exactly 1 succeeds."""
    store = ClinicStore(DATA_PATH)
    
    successes = 0
    failures = 0
    
    def book_task():
        nonlocal successes, failures
        try:
            # pt_0001 booking Dr. Rao on 2026-10-16 09:00
            store.book_appointment("pt_0001", "dr_rao", "2026-10-16", "09:00", "2026-10-01")
            successes += 1
        except ToolError as e:
            if e.code == "SLOT_TAKEN":
                failures += 1
            else:
                raise

    threads = [threading.Thread(target=book_task) for _ in range(20)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    assert successes == 1
    assert failures == 19


def test_leave_and_holiday():
    store = ClinicStore(DATA_PATH)
    
    # Holiday
    res1 = store.search_slots("dr_rao", "2026-10-02", "2026-10-01")
    assert res1["reason"] == "HOLIDAY"
    
    # Dr. Sethi leave
    res2 = store.search_slots("dr_sethi", "2026-10-05", "2026-10-01")
    assert res2["reason"] == "DOCTOR_ON_LEAVE"
    
    # Sunday
    res3 = store.search_slots("dr_rao", "2026-10-04", "2026-10-01")
    assert res3["reason"] == "NOT_A_WORKING_DAY"


def test_patient_lookup():
    store = ClinicStore(DATA_PATH)
    
    # Ambiguous Sharma
    res1 = store.lookup_patient(name="Sharma")
    assert res1["match"] == "multiple"
    assert len(res1["candidates"]) >= 3
    
    # Exact name + phone
    res2 = store.lookup_patient(name="Rajesh Kumar Sharma", phone="9812200011")
    assert res2["match"] == "exact"
    assert res2["candidates"][0]["id"] == "pt_0001"
    
    # Same phone, different people
    res3 = store.lookup_patient(phone="9812200466")
    assert res3["match"] == "multiple"
    assert len(res3["candidates"]) == 2  # Sanjay and Kavita Rawat
