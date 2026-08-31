"""
Verification script confirming disease diagnostic message and city-specific specialist matching.
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
    print("STARTING TEST: VERIFYING DISEASE DIAGNOSTIC & CITY SPECIALIST MATCHING")
    print("=" * 80)

    ts = int(time.time())
    creds = {
        "email": f"city_spec_test_{ts}@healthnavigator.com",
        "password": "Password123!"
    }
    r = requests.post(f"{BASE_URL}/auth/signup", json=creds)
    assert r.status_code == 200, f"Signup failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] Created Isolated Patient Account")

    # Start intake with a city mention: "I live in New York and have hair loss"
    print("\nUser: I live in New York and have hair loss")
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"content": "I live in New York and have hair loss"})
    assert r.status_code == 200
    res = r.json()
    conv_id = res["conversation_id"]
    print_clean(f"Bot: {res['bot_message']['content']}")

    # Proceed through intake questions (quick responses)
    questions_and_replies = [
        ("1 month", "duration"),
        ("sudden", "onset_pattern"),
        ("no other symptoms", "associated_symptoms"),
        ("mild", "severity"),
        ("no pre-existing conditions", "known_conditions"),
        ("no medicines", "medications"),
        ("no allergies", "allergies"),
        ("no exposures", "recent_exposure"),
        ("no emergency symptoms", "safety_red_flags")
    ]

    for reply, step_name in questions_and_replies:
        print(f"\nUser: {reply}")
        r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"conversation_id": conv_id, "content": reply})
        assert r.status_code == 200
        res = r.json()
        bot_reply = res["bot_message"]["content"]
        print_clean(f"Bot: {bot_reply}")

    # Check diagnostic content in final message before booking
    print("\n--- CHECKING DIAGNOSTIC MESSAGE BEFORE BOOKING ---")
    assert "alopecia" in bot_reply.lower(), "Expected diagnosis 'Alopecia / Hair Loss' in final message"
    assert "dermatology" in bot_reply.lower(), "Expected recommendation for 'Dermatology' specialist"
    assert "new york" in bot_reply.lower(), "Expected bot to search for specialists in 'New York'"
    assert "dr. clara song, md" in bot_reply.lower(), "Expected specialist 'Dr. Clara Song, MD' to be returned in NY search"
    print("[PASS] Disease diagnosis, recommended specialty, and New York specialist details fetched successfully!")

    # Confirm booking to trigger doctor selection list
    print("\nUser: Yes, book appointment")
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"conversation_id": conv_id, "content": "Yes, book appointment"})
    assert r.status_code == 200
    res = r.json()
    bot_reply = res["bot_message"]["content"]
    options = res["bot_message"]["followup_options"]
    print_clean(f"Bot: {bot_reply}")
    print_clean(f"Options: {options}")

    # Verify that only the New York specialist is offered as options (not the Bangalore dermatologist Dr. Monish JB)
    assert any("Clara Song" in opt for opt in options), "Expected Dr. Clara Song to be returned as slot option"
    assert not any("Monish JB" in opt for opt in options), "Expected Dr. Monish JB (Bangalore specialist) to be filtered out of New York slots"
    print("[PASS] Specialist slot selection successfully filtered to New York only!")

    print("\n" + "=" * 80)
    print("DISEASE DIAGNOSTIC & CITY SPECIALIST MATCHING TEST PASSED!")
    print("=" * 80)

if __name__ == "__main__":
    run_test()
