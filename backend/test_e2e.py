import time
import os
import requests

BASE_URL = "http://127.0.0.1:8000"

def run_e2e_tests():
    print("=" * 70)
    print("RUNNING COMPREHENSIVE END-TO-END SUITE FOR SUPPORT COPILOT")
    print("=" * 70)

    # 1. Health check
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200, f"Root endpoint failed: {r.text}"
    print("[PASS] 1. Root Health Check Endpoint")

    # 2. Google Auth Signup / Login
    google_req = {"credential": "demo_google_token_e2e_admin@company.com"}
    r = requests.post(f"{BASE_URL}/auth/google", json=google_req)
    assert r.status_code == 200, f"Google auth failed: {r.text}"
    admin_data = r.json()
    admin_token = admin_data["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print(f"[PASS] 2. Google OAuth Authentication (User: {admin_data['user']['email']}, Role: {admin_data['user']['role']})")

    # 3. Customer Account Signup
    ts = int(time.time())
    customer_signup = {
        "email": f"customer_{ts}@e2etest.com",
        "password": "CustomerPassword123!"
    }
    r = requests.post(f"{BASE_URL}/auth/signup", json=customer_signup)
    assert r.status_code == 200, f"Customer signup failed: {r.text}"
    customer_data = r.json()
    customer_token = customer_data["access_token"]
    customer_headers = {"Authorization": f"Bearer {customer_token}"}
    print(f"[PASS] 3. Customer Email Registration (User: {customer_data['user']['email']}, Role: {customer_data['user']['role']})")

    # 4. Auth Verification Endpoint
    r = requests.get(f"{BASE_URL}/auth/me", headers=customer_headers)
    assert r.status_code == 200 and r.json()["email"] == customer_signup["email"]
    print("[PASS] 4. User Profile Authorization (/auth/me)")

    # 5. Knowledge Base Document Ingestion
    policy_doc = (
        "SUPPORT COPILOT ENTERPRISE SLA & POLICY MANUAL\n"
        "1. Response Times: Guaranteed 15-minute response for critical issues.\n"
        "2. Billing: Plans start at $49/mo for Pro and $199/mo for Enterprise.\n"
        "3. Security: All data is encrypted at rest using AES-256 and TLS 1.3 in transit.\n"
        "4. Escalation: High priority complaints automatically create an urgent support ticket."
    )
    files = {"file": ("enterprise_policy.txt", policy_doc.encode("utf-8"), "text/plain")}
    r = requests.post(f"{BASE_URL}/kb/upload", headers=admin_headers, files=files)
    assert r.status_code == 200, f"KB upload failed: {r.text}"
    kb_data = r.json()
    assert kb_data["chunk_count"] > 0
    print(f"[PASS] 5. Knowledge Base Upload & Vector Parsing (Doc ID: {kb_data['id']}, Chunks: {kb_data['chunk_count']})")

    # 6. List KB Documents
    r = requests.get(f"{BASE_URL}/kb/documents", headers=admin_headers)
    assert r.status_code == 200 and len(r.json()) >= 1
    print(f"[PASS] 6. Knowledge Base Document Indexing (Total Docs: {len(r.json())})")

    # 7. RAG Question Answering
    q_rag = {"content": "What is the response time for critical issues?"}
    r = requests.post(f"{BASE_URL}/chat/message", headers=customer_headers, json=q_rag)
    assert r.status_code == 200, f"Chat message failed: {r.text}"
    chat_res = r.json()
    conv_id = chat_res["conversation_id"]
    bot_msg = chat_res["bot_message"]
    assert bot_msg["rag_grounded"] is True
    print(f"[PASS] 7. RAG Grounded Chat Answer (Conv #{conv_id}, Intent: {bot_msg['intent']})")

    # 8. Complaint Auto-Escalation & Ticket Generation
    q_complaint = {
        "conversation_id": conv_id,
        "content": "Your system failed and charged me twice! I want an immediate refund!"
    }
    r = requests.post(f"{BASE_URL}/chat/message", headers=customer_headers, json=q_complaint)
    assert r.status_code == 200, f"Complaint message failed: {r.text}"
    bot_complaint = r.json()["bot_message"]
    assert bot_complaint["escalated"] is True
    print(f"[PASS] 8. Auto-Escalation & Intent Classification (Escalated: {bot_complaint['escalated']}, Reason: {bot_complaint['escalation_reason']})")

    # 9. Thumbs-up Feedback
    fb_data = {"message_id": bot_msg["id"], "feedback": 1}
    r = requests.post(f"{BASE_URL}/chat/feedback", headers=customer_headers, json=fb_data)
    assert r.status_code == 200 and r.json()["feedback"] == 1
    print("[PASS] 9. User Experience Feedback System")

    # 10. Admin Analytics Metrics
    r = requests.get(f"{BASE_URL}/metrics/summary", headers=admin_headers)
    assert r.status_code == 200
    metrics = r.json()
    print(f"[PASS] 10. Admin Analytics Engine (Conversations: {metrics['total_conversations']}, CSAT: {metrics['satisfaction_score']}%)")

    # 11. Support Ticket Queue
    r = requests.get(f"{BASE_URL}/tickets", headers=admin_headers)
    assert r.status_code == 200 and len(r.json()) >= 1
    ticket_id = r.json()[0]["id"]
    print(f"[PASS] 11. Support Ticket Queue Management (Open Tickets: {len(r.json())})")

    # 12. Resolve Ticket & Conversation
    r = requests.patch(f"{BASE_URL}/tickets/{ticket_id}/status", headers=admin_headers, json={"status": "closed"})
    assert r.status_code == 200 and r.json()["status"] == "closed"
    r = requests.post(f"{BASE_URL}/chat/resolve/{conv_id}", headers=customer_headers)
    assert r.status_code == 200
    print("[PASS] 12. Ticket Resolution & Conversation Lifecycle")

    print("=" * 70)
    print("SUCCESS: ALL 12 END-TO-END INTEGRATION TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    run_e2e_tests()
