"""
Verification Test for Clinician Tone and Bathing Onset Detail.
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

def run_test():
    print("=" * 80)
    print("STARTING TEST: VERIFYING BATHING ONSET CLINICIAN REACTION")
    print("=" * 80)

    ts = int(time.time())
    creds = {
        "email": f"bathing_test_{ts}@healthnavigator.com",
        "password": "Password123!"
    }
    r = requests.post(f"{BASE_URL}/auth/signup", json=creds)
    assert r.status_code == 200, f"Signup failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] Created Isolated Patient Account")

    # Turn 1: Primary Complaint (No "sudden" keyword, so onset_pattern stays empty)
    print("\nUser: I am experiencing hair loss.")
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"content": "I am experiencing hair loss."})
    assert r.status_code == 200
    conv_id = r.json()["conversation_id"]
    print_clean(f"Bot: {r.json()['bot_message']['content']}")

    # Turn 2: Duration
    print("\nUser: 1 month")
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"conversation_id": conv_id, "content": "1 month"})
    assert r.status_code == 200
    print_clean(f"Bot: {r.json()['bot_message']['content']}")

    # Turn 3: Onset (Custom text)
    print("\nUser: it does come while i was bathing")
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"conversation_id": conv_id, "content": "it does come while i was bathing"})
    assert r.status_code == 200
    res = r.json()
    bot_reply = res["bot_message"]["content"]
    print_clean(f"Bot: {bot_reply}")

    # Check raw_notes on PatientContext
    raw_notes = res["patient_context"]["raw_notes"]
    print_clean(f"PatientContext raw_notes: {raw_notes}")
    
    assert any("bathing" in note.lower() for note in raw_notes), "Bathing detail should be stored in raw_notes"
    print("[PASS] Bathing detail successfully stored in PatientContext raw_notes")

    assert "bathing" in bot_reply.lower(), "Expected bot reply to acknowledge bathing detail"
    assert "water contact" in bot_reply.lower(), "Expected bot reply to mention water contact"
    print("\n[PASS] Med AI Clinician Acknowledged Bathing Detail Verbatim!")
    print("=" * 80)

if __name__ == "__main__":
    run_test()
