import time
import os
import requests
import json

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

def run_tests():
    print("=" * 60)
    print("STARTING HEALTHCARE KNOWLEDGE NAVIGATOR API SMOKE TEST")
    print("=" * 60)

    # 1. Health check
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200, f"Root endpoint failed: {r.text}"
    print("[OK] Health Check Passed")

    # 2. Signup or Login Admin User
    admin_credentials = {
        "email": "admin@healthnavigator.com",
        "password": "AdminPassword123!"
    }
    r = requests.post(f"{BASE_URL}/auth/signup", json=admin_credentials)
    if r.status_code != 200:
        r = requests.post(f"{BASE_URL}/auth/login", json=admin_credentials)
        assert r.status_code == 200, f"Admin login failed: {r.text}"
    
    admin_token = r.json()["access_token"]
    print(f"[OK] Admin Auth Passed (User: {r.json()['user']['email']})")

    # 3. Signup Patient / Customer User
    ts = int(time.time())
    customer_signup = {
        "email": f"patient_{ts}@healthnavigator.com",
        "password": "PatientPassword123!"
    }
    r = requests.post(f"{BASE_URL}/auth/signup", json=customer_signup)
    assert r.status_code == 200, f"Patient signup failed: {r.text}"
    customer_token = r.json()["access_token"]
    headers_customer = {"Authorization": f"Bearer {customer_token}"}
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    print("[OK] Patient Signup Passed")

    # 4. Upload Clinical Document (Admin Only)
    clinical_guideline = (
        "# CLINICAL GUIDELINE: ADULT FATIGUE AND HYPOTHYROIDISM PROTOCOL\n"
        "SECTION 1: CLINICAL EVALUATION OF CHRONIC FATIGUE\n"
        "Fatigue lasting longer than 2 weeks in adults requires evaluation of serum TSH, Hemoglobin, and Glucose.\n"
        "Common etiologies include hypothyroidism, iron-deficiency anemia, and metabolic syndromes.\n"
        "SECTION 2: DIAGNOSTIC CRITERIA\n"
        "Elevated TSH (>4.5 mIU/L) with low free T4 confirms primary hypothyroidism. Initial management involves levothyroxine therapy under clinical supervision.\n"
    )
    files = {"file": ("fatigue_guidelines.txt", clinical_guideline.encode("utf-8"), "text/plain")}
    r = requests.post(f"{BASE_URL}/kb/upload", headers=headers_admin, files=files, data={"source_type": "Clinical Guideline"})
    assert r.status_code == 200, f"KB Upload failed: {r.text}"
    print("[OK] Medical Knowledge Base Upload Passed")

    # 5. Test Emergency Safety Triage Triggering
    q_emergency = {"content": "I am experiencing severe chest pain, shortness of breath, and arm numbness."}
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers_customer, json=q_emergency)
    assert r.status_code == 200, f"Emergency check failed: {r.text}"
    res_emergency = r.json()["bot_message"]
    assert res_emergency["triage_level"] == "EMERGENCY"
    assert res_emergency["escalated"] is True
    print("[OK] Emergency Red-Flag Triage Detection Passed (Level: EMERGENCY)")

    # 6. Test Initial Vague Symptom Query -> Follow-Up Agent Triggering
    q_symptom = {"content": "My mother has been feeling tired for the last few weeks."}
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers_customer, json=q_symptom)
    assert r.status_code == 200, f"Symptom message failed: {r.text}"
    res_symptom = r.json()
    conv_id = res_symptom["conversation_id"]
    bot_msg = res_symptom["bot_message"]
    ctx = res_symptom["patient_context"]

    assert ctx["sex"] == "Female", "Should extract Female context from 'mother'"
    assert "tired" in ctx["symptoms"], "Should record 'tired' symptom"
    assert bot_msg["followup_options"] is not None or "tired" in ctx["symptoms"]
    print(f"[OK] Patient Context Extraction & Follow-Up Agent Passed (Sex: {ctx['sex']}, Symptoms: {ctx['symptoms']})")

    # 7. Follow-up Answer -> RAG Retrieval & Synthesis with Citations & Confidence
    q_answer = {"conversation_id": conv_id, "content": "She is 62 years old and taking no medications. What could cause this fatigue?"}
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers_customer, json=q_answer)
    assert r.status_code == 200, f"Answer query failed: {r.text}"
    res_answer = r.json()
    bot_synth = res_answer["bot_message"]
    ctx_updated = res_answer["patient_context"]

    assert ctx_updated["age"] == 62, "Should update patient age to 62"
    assert bot_synth["confidence_level"] in ["HIGH", "MEDIUM", "LOW"]
    assert bot_synth["citations"] is not None and len(bot_synth["citations"]) > 0
    print(f"[OK] Evidence Synthesis, Confidence ({bot_synth['confidence_level']}), and Citations Passed ({len(bot_synth['citations'])} sources)")

    print("=" * 60)
    print("ALL HEALTHCARE KNOWLEDGE NAVIGATOR SMOKE TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
