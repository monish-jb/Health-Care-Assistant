"""
Verification script confirming that mid-flow general questions get answered directly
without disrupting or resetting the conversation state.
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
    print("STARTING TEST: VERIFYING MID-FLOW GENERAL QUESTION EXPLANATION")
    print("=" * 80)

    ts = int(time.time())
    creds = {
        "email": f"mid_flow_test_{ts}@healthnavigator.com",
        "password": "Password123!"
    }
    r = requests.post(f"{BASE_URL}/auth/signup", json=creds)
    assert r.status_code == 200, f"Signup failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] Created Isolated Patient Account")

    # Start intake: "I have a sudden fever"
    print("\nUser: I have a sudden fever")
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"content": "I have a sudden fever"})
    assert r.status_code == 200
    res = r.json()
    conv_id = res["conversation_id"]
    last_bot_reply = res['bot_message']['content']
    print_clean(f"Bot: {last_bot_reply}")

    # Step 2: Duration question. Let's ask "who is a pulmonologist" instead of answering!
    print("\nUser: who is a pulmonologist")
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"conversation_id": conv_id, "content": "who is a pulmonologist"})
    assert r.status_code == 200
    res = r.json()
    bot_reply = res["bot_message"]["content"]
    print_clean(f"Bot: {bot_reply}")

    # Verify that the question was answered and the previous duration prompt was re-shown
    assert "pulmonologist" in bot_reply.lower(), "Expected definition of pulmonologist in reply"
    assert "anyway" in bot_reply.lower(), "Expected the bot to prompt the user back to the conversation flow"
    assert last_bot_reply.split("\n\n")[-1] in bot_reply, "Expected the previous bot question to be appended at the end"
    print("[PASS] General question answered directly and previous question appended correctly!")

    # Verify patient context is intact and step did not reset
    ctx = res["patient_context"]
    assert ctx["current_step"] == 2, f"Expected current step to remain at 2, got {ctx['current_step']}"
    print("[PASS] Conversation state and patient context preserved without resetting!")

    # Answer the duration question now to see if we can continue smoothly
    print("\nUser: 3 days")
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"conversation_id": conv_id, "content": "3 days"})
    assert r.status_code == 200
    res = r.json()
    bot_reply = res["bot_message"]["content"]
    print_clean(f"Bot: {bot_reply}")

    ctx = res["patient_context"]
    assert ctx["current_step"] > 2, "Expected conversation to advance to next step"
    print("[PASS] Conversation continued seamlessly after the general question detour!")

    print("\n" + "=" * 80)
    print("MID-FLOW GENERAL QUESTION VERIFICATION PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_test()
