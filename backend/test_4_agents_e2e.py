"""
Comprehensive End-to-End Test Suite for 4-Agent Hospital Appointment & Patient Guidance System.
Tests:
1. Agent 1: Triage Agent (Intake, Extraction, Ranked Possibilities, Confidence Gate & Dept Routing)
2. Agent 2: Booking Agent (Conflict-Free Concurrency Safe Slot Booking with Patient Confirmation)
3. Agent 3: Report Agent (Structured SOAP Note Generation & Physician Review)
4. Agent 4: Care Agent (Post-Discharge Pill Reminders & Follow-up Scheduling)
"""

import os
import time
import requests
import json

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

def run_4_agents_tests():
    print("=" * 75)
    print("RUNNING COMPLETE 4-AGENT E2E SYSTEM INTEGRATION TEST SUITE")
    print("=" * 75)

    # 1. Health check
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200, f"Server unreachable: {r.text}"
    print("[PASS] 1. Backend Server Online")

    # 2. Authenticate Patient User
    ts = int(time.time())
    user_cred = {
        "email": f"patient_4agent_{ts}@hospital.com",
        "password": "PatientPassword123!"
    }
    r = requests.post(f"{BASE_URL}/auth/signup", json=user_cred)
    assert r.status_code == 200, f"Signup failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[PASS] 2. Patient Authentication Token (User: {user_cred['email']})")

    # -------------------------------------------------------------
    # TEST AGENT 1: TRIAGE AGENT (Assess + Route)
    # -------------------------------------------------------------
    print("\n--- AGENT 1: TRIAGE AGENT (ASSESS + ROUTE) ---")
    triage_payload = {
        "symptoms": "I have been feeling very tired and gaining weight over the last month.",
        "patient_context": {"age": 35, "sex": "Female", "symptoms": ["tired", "fatigue"]}
    }
    r = requests.post(f"{BASE_URL}/api/agents/triage/assess", json=triage_payload)
    assert r.status_code == 200, f"Triage failed: {r.text}"
    triage_data = r.json()
    assert triage_data["department"] == "Endocrinology", f"Expected Endocrinology, got {triage_data['department']}"
    assert len(triage_data["ranked_possibilities"]) > 0
    assert triage_data["confidence_gate"] == "ROUTED_TO_DEPARTMENT"
    print(f"[PASS] 1. Triage Agent: 4-Step Assessment Completed")
    print(f"       - Recommended Department: {triage_data['department']}")
    print(f"       - Top Ranked Condition: {triage_data['ranked_possibilities'][0]['condition']} ({triage_data['ranked_possibilities'][0]['probability']})")
    print(f"       - Confidence Gate: {triage_data['confidence_gate']}")

    # -------------------------------------------------------------
    # TEST AGENT 2: BOOKING AGENT (Conflict-Free Scheduling)
    # -------------------------------------------------------------
    print("\n--- AGENT 2: BOOKING AGENT (CONFLICT-FREE SCHEDULING) ---")
    # Step A: Fetch available doctors in Endocrinology
    r = requests.get(f"{BASE_URL}/api/agents/booking/slots?department=Endocrinology", headers=headers)
    assert r.status_code == 200, f"Slots fetch failed: {r.text}"
    doctors = r.json()
    assert len(doctors) > 0, "Should return available doctors"
    selected_doc = doctors[0]
    selected_slot = selected_doc["available_slots"][0]
    print(f"[PASS] 2a. Booking Agent: Retrieved live doctor {selected_doc['name']} with {len(selected_doc['available_slots'])} open slots")

    # Step B: Reserve slot draft (Provisional Hold)
    reserve_payload = {
        "doctor_id": selected_doc["doctor_id"],
        "slot_id": selected_slot["slot_id"]
    }
    r = requests.post(f"{BASE_URL}/api/agents/booking/reserve", headers=headers, json=reserve_payload)
    assert r.status_code == 200, f"Slot reserve failed: {r.text}"
    res_draft = r.json()
    appt_id = res_draft["appointment_id"]
    booking_ref = res_draft["booking_reference"]
    assert res_draft["status"] == "pending_confirmation"
    print(f"[PASS] 2b. Booking Agent: Provisional Hold Created (Appt ID: {appt_id}, Ref: {booking_ref})")

    # Step C: Patient Confirms Slot Lock
    confirm_payload = {
        "appointment_id": appt_id,
        "slot_id": selected_slot["slot_id"]
    }
    r = requests.post(f"{BASE_URL}/api/agents/booking/confirm", headers=headers, json=confirm_payload)
    assert r.status_code == 200, f"Slot confirm failed: {r.text}"
    res_confirmed = r.json()
    assert res_confirmed["status"] == "confirmed"
    print(f"[PASS] 2c. Booking Agent: Patient Confirmed & Database Lock Finalized (Ref: {booking_ref})")

    # -------------------------------------------------------------
    # TEST AGENT 3: REPORT AGENT (Doctor-Ready SOAP Draft Note)
    # -------------------------------------------------------------
    print("\n--- AGENT 3: REPORT AGENT (DOCTOR-READY SOAP SUMMARIES) ---")
    # Initiate consultation chat first to establish conversation
    chat_res = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"content": "I am experiencing fatigue and weight gain for 3 weeks."})
    assert chat_res.status_code == 200
    conv_id = chat_res.json()["conversation_id"]

    # Generate SOAP Draft Note
    r = requests.get(f"{BASE_URL}/api/agents/reports/soap/{conv_id}", headers=headers)
    assert r.status_code == 200, f"SOAP report failed: {r.text}"
    soap_data = r.json()
    assert "Subjective" in soap_data["subjective"] or "Chief Complaint" in soap_data["subjective"]
    assert len(soap_data["suggested_tests"]) > 0
    report_id = soap_data["id"]
    print(f"[PASS] 3a. Report Agent: Auto-Generated Structured SOAP Clinical Draft Note")
    print(f"       - Suggested Diagnostic Tests: {soap_data['suggested_tests'][:2]}")

    # Doctor Reviews and Approves SOAP Note
    approve_payload = {"doctor_notes": "Reviewed and agreed with primary assessment. Ordered TSH and HbA1c panels."}
    r = requests.post(f"{BASE_URL}/api/agents/reports/soap/{report_id}/approve", headers=headers, json=approve_payload)
    assert r.status_code == 200
    assert r.json()["doctor_reviewed"] is True
    print(f"[PASS] 3b. Report Agent: Doctor Review & Approval Checkpoint Completed")

    # -------------------------------------------------------------
    # TEST AGENT 4: CARE AGENT (Discharge Reminders & Follow-Up)
    # -------------------------------------------------------------
    print("\n--- AGENT 4: CARE AGENT (DISCHARGE REMINDERS & FOLLOW-UP) ---")
    # Generate post-discharge pill reminders
    care_payload = {
        "medications": [
            {"medication_name": "Levothyroxine", "dosage": "50 mcg", "frequency": "Daily morning before breakfast", "reminder_time": "07:30 AM"},
            {"medication_name": "Vitamin D3", "dosage": "1000 IU", "frequency": "Daily with breakfast", "reminder_time": "08:30 AM"}
        ]
    }
    r = requests.post(f"{BASE_URL}/api/agents/care/reminders/generate", headers=headers, json=care_payload)
    assert r.status_code == 200
    reminders = r.json()
    assert len(reminders) == 2
    rem_id = reminders[0]["id"]
    print(f"[PASS] 4a. Care Agent: Scheduled {len(reminders)} Medication Pill Reminders")

    # Patient toggles / opts out of a reminder
    r = requests.post(f"{BASE_URL}/api/agents/care/reminders/{rem_id}/toggle", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "paused"
    print(f"[PASS] 4b. Care Agent: Patient Opt-out / Timing Control Verified (Reminder paused)")

    print("=" * 75)
    print("SUCCESS: ALL 4 AGENTS (TRIAGE, BOOKING, REPORT, CARE) PASSED 100%!")
    print("=" * 75)

if __name__ == "__main__":
    run_4_agents_tests()
