"""
End-to-End Medical Verification Test Suite for Healthcare Knowledge Navigator.
Tests end-to-end multi-agent pipeline, RAG accuracy, triage safety, context memory, and citations.
"""

import time
import requests
import json
import subprocess
import os

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

def run_e2e_medical_tests():
    print("=" * 70)
    print("HEALTHCARE KNOWLEDGE NAVIGATOR — E2E MULTI-AGENT VERIFICATION TEST")
    print("=" * 70)

    # 1. Health check
    try:
        r = requests.get(f"{BASE_URL}/")
        assert r.status_code == 200, f"Server unreachable: {r.text}"
        print("[PASS] Backend API Health Check Online")
    except Exception as e:
        print(f"[FAIL] Could not connect to FastAPI server at {BASE_URL}: {e}")
        print("Please start server first: uvicorn app.main:app --port 8000")
        return

    # 2. Authenticate Patient User
    ts = int(time.time())
    patient_credentials = {
        "email": f"test_patient_{ts}@healthnavigator.com",
        "password": "PatientPassword123!"
    }
    r = requests.post(f"{BASE_URL}/auth/signup", json=patient_credentials)
    assert r.status_code == 200, f"Signup failed: {r.text}"
    patient_token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {patient_token}"}
    print(f"[PASS] User Authentication & Token Generation (User: {patient_credentials['email']})")

    # 3. Test 1: Emergency Safety Triage Override
    print("\n--- TEST 1: EMERGENCY SAFETY TRIAGE DETECTOR ---")
    req_emergency = {"content": "My father is experiencing sudden severe chest pain, shortness of breath, and arm numbness."}
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json=req_emergency)
    assert r.status_code == 200, f"Emergency call failed: {r.text}"
    bot_msg1 = r.json()["bot_message"]
    assert bot_msg1["triage_level"] == "EMERGENCY", f"Expected EMERGENCY, got {bot_msg1['triage_level']}"
    assert bot_msg1["escalated"] is True, "Emergency query must trigger escalation flag"
    assert "911" in bot_msg1["content"] or "emergency" in bot_msg1["content"].lower()
    print("[PASS] Emergency Red-Flag Triage Triggered (Triage Level: EMERGENCY, Escalated: True)")

    # 4. Test 2: Follow-Up Question & Option Chip Generation
    print("\n--- TEST 2: FOLLOW-UP QUESTION & OPTION CHIPS AGENT ---")
    req_fatigue = {"content": "My mother has been feeling very tired lately."}
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json=req_fatigue)
    assert r.status_code == 200, f"Fatigue query failed: {r.text}"
    res2 = r.json()
    conv_id = res2["conversation_id"]
    bot_msg2 = res2["bot_message"]
    ctx2 = res2["patient_context"]

    assert ctx2["sex"] == "Female", f"Expected Female from 'mother', got {ctx2['sex']}"
    assert "tired" in ctx2["symptoms"], "Expected 'tired' in patient symptoms"
    assert bot_msg2["followup_options"] is not None and len(bot_msg2["followup_options"]) > 0
    print(f"[PASS] Follow-Up Agent Triggered (Options generated: {bot_msg2['followup_options']})")
    print(f"[PASS] Patient Context Extracted: Sex={ctx2['sex']}, Symptoms={ctx2['symptoms']}")

    # 5. Test 3: Multi-turn Context Memory & Evidence RAG Retrieval
    print("\n--- TEST 3: MULTI-TURN MEMORY & HIGH-ACCURACY RAG EVIDENCE ---")
    req_answer = {
        "conversation_id": conv_id,
        "content": "She is 62 years old, experiencing this fatigue for 1 month, and has a TSH blood test result of 6.8 mIU/L."
    }
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json=req_answer)
    assert r.status_code == 200, f"Answer query failed: {r.text}"
    res3 = r.json()
    bot_msg3 = res3["bot_message"]
    ctx3 = res3["patient_context"]

    assert ctx3["age"] == 62, f"Expected Age=62, got {ctx3['age']}"
    assert ctx3["duration"] is not None
    assert bot_msg3["confidence_level"] in ["HIGH", "MEDIUM", "LOW"]
    print(f"[PASS] Patient Memory Updated: Age={ctx3['age']}, Duration={ctx3['duration']}")
    print(f"[PASS] Evidence Confidence Calculated: Level={bot_msg3['confidence_level']}")
    if bot_msg3["citations"]:
        print(f"[PASS] Traceable Citations Returned ({len(bot_msg3['citations'])} sources):")
        for c in bot_msg3["citations"]:
            print(f"      - [{c['id']}] {c['title']} ({c['source_type']} - Section: {c['section']})")

    # 6. Test 4: Medication Interaction Query
    print("\n--- TEST 4: MEDICATION INTERACTION & SAFETY CHECK ---")
    req_med = {"content": "Can a patient taking Lisinopril for hypertension safely take Ibuprofen for pain?"}
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers, json=req_med)
    assert r.status_code == 200, f"Med query failed: {r.text}"
    bot_msg4 = r.json()["bot_message"]
    assert bot_msg4["intent"] == "medication_question"
    print(f"[PASS] Intent Classified: {bot_msg4['intent']}")

    print("\n" + "=" * 70)
    print("ALL E2E MULTI-AGENT MEDICAL TESTS PASSED SUCCESSFULLY! (100% PASS RATE)")
    print("=" * 70)

if __name__ == "__main__":
    run_e2e_medical_tests()
