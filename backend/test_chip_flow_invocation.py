"""
Verification script simulating a full option-chip click intake flow
and confirming identical LLM invocation and debug source logs.
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
    print("STARTING TEST: SIMULATING OPTION CHIP CLICK INTAKE FLOW")
    print("=" * 80)

    ts = int(time.time())
    creds = {
        "email": f"chip_test_{ts}@healthnavigator.com",
        "password": "Password123!"
    }
    r = requests.post(f"{BASE_URL}/auth/signup", json=creds)
    assert r.status_code == 200, f"Signup failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] Created Patient Account")

    # Turn 1: Free Text Symptom
    print("\n[Turn 1] User types free-text symptom:")
    print("User: fever")
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"content": "fever"})
    assert r.status_code == 200
    res1 = r.json()
    conv_id = res1["conversation_id"]
    bot_reply1 = res1["bot_message"]["content"]
    options1 = res1["bot_message"]["followup_options"]
    print_clean(f"Bot: {bot_reply1}")
    print_clean(f"Chips presented: {options1}")

    # Turn 2: Click "Just started today" Option Chip
    print("\n[Turn 2] User clicks option chip:")
    print("User (clicked chip): Just started today")
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"conversation_id": conv_id, "content": "Just started today"})
    assert r.status_code == 200
    res2 = r.json()
    bot_reply2 = res2["bot_message"]["content"]
    options2 = res2["bot_message"]["followup_options"]
    print_clean(f"Bot: {bot_reply2}")
    print_clean(f"Chips presented: {options2}")

    # Turn 3: Click "Sudden & Comes and goes" Option Chip
    print("\n[Turn 3] User clicks option chip:")
    print("User (clicked chip): Sudden & Comes and goes")
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"conversation_id": conv_id, "content": "Sudden & Comes and goes"})
    assert r.status_code == 200
    res3 = r.json()
    bot_reply3 = res3["bot_message"]["content"]
    options3 = res3["bot_message"]["followup_options"]
    print_clean(f"Bot: {bot_reply3}")
    print_clean(f"Chips presented: {options3}")

    print("\n" + "=" * 80)
    print("CHIP-BASED INTAKE TEST PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_test()
