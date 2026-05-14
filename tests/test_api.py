from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def auth_headers(username: str = "admin", password: str = "KayraAdmin2026!") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["indexed_chunks"] > 0
    assert response.json()["app_name"] == "Kayra"


def test_chat_requires_auth():
    response = client.post("/api/chat", json={"message": "VPN hata verirse ne yapmaliyim?"})
    assert response.status_code == 401


def test_chat_endpoint_returns_sources():
    response = client.post(
        "/api/chat",
        json={"message": "VPN hata verirse ne yapmaliyim?"},
        headers=auth_headers(),
    )
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
    assert len(topics) >= 6
    assert any(topic["id"] == "privacy" for topic in topics)


def test_enterprise_overview_endpoint_requires_admin():
    response = client.get("/api/enterprise/overview", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["product_name"] == "Kayra Enterprise Assistant"
    assert payload["metrics"]
    assert payload["integrations"]
    assert payload["security_controls"]


def test_ticket_draft_endpoint_classifies_it_request():
    response = client.post(
        "/api/tickets/draft",
        json={"message": "VPN baglantisi hata veriyor ve erisim saglayamiyorum", "priority": "acil"},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["category"] == "IT Destek"
    assert payload["escalation_required"] is True


def test_registered_user_cannot_access_admin_overview():
    username = f"user_{uuid4().hex[:8]}"
    create = client.post(
        "/api/admin/users",
        json={"username": username, "password": "secret123", "email": "test@example.com"},
        headers=auth_headers(),
    )
    assert create.status_code == 200
    headers = auth_headers(username, "secret123")

    response = client.get("/api/enterprise/overview", headers=headers)
    assert response.status_code == 403


def test_public_registration_is_not_available():
    response = client.post(
        "/api/auth/register",
        json={"username": "no_self_signup", "password": "secret123"},
    )
    assert response.status_code == 404


def test_admin_can_manage_users_from_database():
    username = f"dbuser_{uuid4().hex[:8]}"
    headers = auth_headers()
    create = client.post(
        "/api/admin/users",
        json={
            "username": username,
            "password": "secret123",
            "email": "dbuser@example.com",
            "display_name": "DB User",
            "role": "it",
        },
        headers=headers,
    )
    assert create.status_code == 200
    assert create.json()["role"] == "it"

    users = client.get("/api/admin/users", headers=headers)
    assert users.status_code == 200
    assert any(user["username"] == username for user in users.json()["users"])

    login = client.post("/api/auth/login", json={"username": username, "password": "secret123"})
    assert login.status_code == 200
