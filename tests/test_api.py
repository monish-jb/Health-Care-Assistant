from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").status_code == 200


def test_chat_emergency_short_circuits():
    r = client.post("/chat", json={"session_id": "session-123", "message": "I have severe chest pain"})
    assert r.status_code == 200 and r.json()["emergency"] is True


def test_chat_validation():
    assert client.post("/chat", json={"session_id": "x", "message": ""}).status_code == 422


def test_predict_503_without_model():
    r = client.post("/predict", json={"symptoms": ["fever"]})
    assert r.status_code in (200, 503)
