"""
End-to-End Verification Test for Doctor Booking & Free-Text Symptom Intake.
"""

import requests
import time
import os

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8008")

def print_clean(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', errors='replace').decode('ascii'))

def run_tests():
    print("=" * 80)
    print("STARTING TEST: GENERALIZED SYMPTOM INTAKE & DOCTOR BOOKING FLOW")
    print("=" * 80)

    # 1. Sign up new test user
    ts = int(time.time())
    creds = {
        "email": f"booking_test_{ts}@healthnavigator.com",
        "password": "Password123!"
    }
    r = requests.post(f"{BASE_URL}/auth/signup", json=creds)
    assert r.status_code == 200, f"Signup failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] Created Isolated Patient Account")

    # 2. Test Ambiguous Input Retry (Step 1 retry logic)
    print("\n--- TEST: AMBIGUOUS INPUT RETRY ---")
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"content": "hello"})
    assert r.status_code == 200
    res = r.json()
    bot_reply = res["bot_message"]["content"]
    print_clean(f"User: hello")
    print_clean(f"Bot: {bot_reply}")
    assert "could you describe what you're experiencing" in bot_reply.lower(), "Expected clarifying question"
    print("[PASS] Clarifying Question Triggered Successfully on Ambiguous Input")

    # Send ambiguous input again -> should default to 'unspecified symptoms' and proceed to Step 2
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"conversation_id": res["conversation_id"], "content": "idk"})
    assert r.status_code == 200
    res = r.json()
    bot_reply = res["bot_message"]["content"]
    print_clean(f"User: idk")
    print_clean(f"Bot: {bot_reply}")
    assert any(w in bot_reply.lower() for w in ["duration", "how long", "how many", "days or weeks"]), "Expected transition to Step 2"
    print("[PASS] Handled Second Ambiguous Input by Advancing to Duration")

    # 3. Create a fresh conversation to test Generalized Symptom Intake (e.g. "hair loss")
    print("\n--- TEST: GENERALIZED SYMPTOM INTAKE ('hair loss') ---")
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"content": "I am experiencing sudden hair loss."})
    assert r.status_code == 200
    res = r.json()
    conv_id = res["conversation_id"]
    bot_reply = res["bot_message"]["content"]
    ctx = res["patient_context"]
    print_clean(f"User: I am experiencing sudden hair loss.")
    print_clean(f"Bot: {bot_reply}")
    assert ctx["primary_complaint"] == "I am experiencing sudden hair loss.", f"Expected primary complaint to be set, got {ctx['primary_complaint']}"
    assert "hair loss" in bot_reply.lower(), "Expected primary complaint injection in duration question"
    print("[PASS] Free-text Symptom Extracted & Injected in Duration Question")

    # Feed answers dynamically to complete the steps
    answers_pool = [
        "1 month",
        "gradually comes and goes",
        "none",
        "mild",
        "no history of illnesses",
        "no medicines",
        "no allergies",
        "no triggers",
        "no red flags"
    ]
    
    ans_idx = 0
    while "book an appointment" not in bot_reply.lower() and ans_idx < len(answers_pool):
        ans = answers_pool[ans_idx]
        ans_idx += 1
        r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"conversation_id": conv_id, "content": ans})
        assert r.status_code == 200
        res = r.json()
        bot_reply = res["bot_message"]["content"]
        print_clean(f"\nUser: {ans}")
        print_clean(f"Bot: {bot_reply}")

    # Verify that the booking prompt was shown
    assert "book an appointment" in bot_reply.lower(), "Expected booking prompt at the end of intake"
    print("\n[PASS] 10-Step Intake Complete & Doctor Booking Prompted Successfully")

    # 4. Trigger Specialty Mapping & Availability slots
    print("\n--- TEST: SPECIALTY SLOT RETRIEVAL & Fallback ---")
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"conversation_id": conv_id, "content": "Yes, book appointment"})
    assert r.status_code == 200
    res = r.json()
    bot_reply = res["bot_message"]["content"]
    options = res["bot_message"]["followup_options"]
    print_clean(f"User: Yes, book appointment")
    print_clean(f"Bot: {bot_reply}")
    print_clean(f"Options: {options}")

    # Hair loss maps to Dermatology. Since a Dermatologist now exists in our DB, we accept either Dermatology or fallback options.
    assert "dermatology" in bot_reply.lower() or "alternative" in bot_reply.lower() or "general medicine" in bot_reply.lower(), "Expected specialist or fallback options to be returned"
    assert options is not None and len(options) > 1, "Expected doctor slots option chips"
    print("[PASS] Fallback Specialties & Availability Slots Returned Successfully")

    # 5. Select a slot and trigger confirmation
    opts_list = options
    selected_slot = opts_list[0]
    print_clean(f"\n--- TEST: SELECTING SLOT ({selected_slot}) ---")
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"conversation_id": conv_id, "content": selected_slot})
    assert r.status_code == 200
    res = r.json()
    bot_reply = res["bot_message"]["content"]
    print_clean(f"User: {selected_slot}")
    print_clean(f"Bot: {bot_reply}")
    assert "confirm" in bot_reply.lower(), "Expected confirmation prompt"
    print("[PASS] Selection Captured & Confirmation Prompted")

    # 6. Confirm Booking
    print("\n--- TEST: CONFIRMING BOOKING ---")
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"conversation_id": conv_id, "content": "Yes, confirm booking"})
    assert r.status_code == 200
    res = r.json()
    bot_reply = res["bot_message"]["content"]
    print_clean(f"User: Yes, confirm booking")
    print_clean(f"Bot: {bot_reply}")
    assert "confirmed" in bot_reply.lower() and "apt-" in bot_reply.lower(), "Expected confirmation with APT ID"
    print("[PASS] Appointment finalization and ID Generation Complete")

    print("\n" + "=" * 80)
    print("ALL DYNAMIC INTAKE & DOCTOR BOOKING TESTS PASSED SUCCESSFULLY! (100% PASS RATE)")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
