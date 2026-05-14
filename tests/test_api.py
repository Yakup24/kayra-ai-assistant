from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["indexed_chunks"] > 0
    assert response.json()["app_name"] == "Kayra"


def test_chat_endpoint_returns_sources():
    response = client.post("/api/chat", json={"message": "VPN hata verirse ne yapmalıyım?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"]
    assert payload["sources"]
    assert payload["confidence"] > 0
    assert payload["domain"] == "IT destek"
    assert payload["next_actions"]


def test_topics_endpoint_returns_corporate_topics():
    response = client.get("/api/topics")
    assert response.status_code == 200
    topics = response.json()["topics"]
    assert len(topics) >= 5
    assert any(topic["id"] == "privacy" for topic in topics)
