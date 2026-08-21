"""
Mobile API Integration Verification Test Suite.
Tests mobile config handshake, standalone triage, and mobile chat endpoint.
"""

import os
import time
import requests

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

def run_mobile_api_tests():
    print("=" * 70)
    print("RUNNING MOBILE API VERIFICATION SUITE")
    print("=" * 70)

    # 1. Health Check
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200, f"Server unreachable: {r.text}"
    print("[PASS] 1. Root Backend Health Check")

    # 2. Mobile Config Handshake Endpoint
    r = requests.get(f"{BASE_URL}/mobile/api/config")
    assert r.status_code == 200, f"Mobile config endpoint failed: {r.text}"
    config = r.json()
    assert "llm_provider" in config
    assert "rag_active" in config
    print(f"[PASS] 2. Mobile Config Handshake (/mobile/api/config - Provider: {config['llm_provider']}, RAG Active: {config['rag_active']})")

    # 3. Mobile Standalone Quick Triage - Emergency Check
    q_emerg = {"symptoms": "Sudden severe chest pain and arm numbness"}
    r = requests.post(f"{BASE_URL}/mobile/api/triage", json=q_emerg)
    assert r.status_code == 200, f"Mobile triage failed: {r.text}"
    triage_emerg = r.json()
    assert triage_emerg["triage_level"] == "EMERGENCY"
    assert triage_emerg["is_emergency"] is True
    print(f"[PASS] 3. Mobile Standalone Triage (Emergency Level: {triage_emerg['triage_level']})")

    # 4. Mobile Standalone Quick Triage - Routine Check
    q_routine = {"symptoms": "Mild headache for two days"}
    r = requests.post(f"{BASE_URL}/mobile/api/triage", json=q_routine)
    assert r.status_code == 200
    triage_routine = r.json()
    assert triage_routine["is_emergency"] is False
    print(f"[PASS] 4. Mobile Standalone Triage (Routine Level: {triage_routine['triage_level']})")

    # 5. Authenticate Mobile User
    ts = int(time.time())
    user_cred = {
        "email": f"mobile_patient_{ts}@app.com",
        "password": "MobilePassword123!"
    }
    r = requests.post(f"{BASE_URL}/auth/signup", json=user_cred)
    assert r.status_code == 200, f"Mobile signup failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[PASS] 5. Mobile User Authentication Token (User: {user_cred['email']})")

    # 6. Mobile Chat Endpoint - Followup Context Trigger
    chat_req = {"content": "I am feeling very tired lately."}
    r = requests.post(f"{BASE_URL}/mobile/api/chat", headers=headers, json=chat_req)
    assert r.status_code == 200, f"Mobile chat failed: {r.text}"
    res = r.json()
    conv_id = res["conversation_id"]
    assert res["reply"] is not None
    print(f"[PASS] 6. Mobile Chat Endpoint (/mobile/api/chat - Conv #{conv_id}, Latency: {res['response_time_ms']}ms)")

    print("=" * 70)
    print("SUCCESS: ALL MOBILE API INTEGRATION TESTS PASSED 100%!")
    print("=" * 70)

if __name__ == "__main__":
    run_mobile_api_tests()
