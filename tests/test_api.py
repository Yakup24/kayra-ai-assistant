from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.rate_limit import RateLimiter


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
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-request-id"]


def test_rate_limiter_blocks_after_configured_limit():
    limiter = RateLimiter()
    assert limiter.check("login:127.0.0.1:test", limit=2, window_seconds=60) == (True, 0)
    assert limiter.check("login:127.0.0.1:test", limit=2, window_seconds=60) == (True, 0)
    allowed, retry_after = limiter.check("login:127.0.0.1:test", limit=2, window_seconds=60)
    assert allowed is False
    assert retry_after > 0


def test_chat_requires_auth():
    response = client.post("/api/chat", json={"message": "VPN hata verirse ne yapmaliyim?"})
    assert response.status_code == 401


def test_login_returns_refresh_token_and_refresh_endpoint_renews_access():
    login = client.post("/api/auth/login", json={"username": "admin", "password": "KayraAdmin2026!"})
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]
    assert refresh_token

    refresh = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh.status_code == 200
    assert refresh.json()["token"]
    assert refresh.json()["refresh_token"]
    assert refresh.json()["user"]["role"] == "admin"


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


def test_chat_turns_source_into_step_by_step_resolution():
    response = client.post(
        "/api/chat",
        json={"message": "VPN nasil kurulur adim adim anlat"},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert "uygulanabilir ad" in payload["answer"]
    assert "1." in payload["answer"]
    assert any(action["label"] == "Adım adım çöz" for action in payload["next_actions"])


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


def test_ticket_lifecycle_persists_to_database():
    headers = auth_headers()
    create = client.post(
        "/api/tickets",
        json={"message": "VPN erisim sorunu var", "priority": "acil"},
        headers=headers,
    )
    assert create.status_code == 200
    ticket = create.json()
    assert ticket["id"].startswith("KAYRA-")
    assert ticket["status"] == "open"
    assert ticket["sla_minutes"] == 480
    assert ticket["sla_status"] == "active"
    assert ticket["sla_due_at"]

    update = client.patch(
        f"/api/admin/tickets/{ticket['id']}",
        json={"status": "resolved", "assignee": "it-team"},
        headers=headers,
    )
    assert update.status_code == 200
    assert update.json()["status"] == "resolved"
    assert update.json()["resolution_score"] is not None
    assert update.json()["sla_status"] == "met"

    tickets = client.get("/api/admin/tickets", headers=headers)
    assert tickets.status_code == 200
    assert any(item["id"] == ticket["id"] for item in tickets.json()["tickets"])

    events = client.get(f"/api/admin/tickets/{ticket['id']}/events", headers=headers)
    assert events.status_code == 200
    event_types = [event["event_type"] for event in events.json()["events"]]
    assert "created" in event_types
    assert "status_changed" in event_types


def test_admin_can_list_documents_and_toggle_integrations():
    headers = auth_headers()
    docs = client.get("/api/admin/documents", headers=headers)
    assert docs.status_code == 200
    assert docs.json()["documents"]

    integrations = client.get("/api/admin/integrations", headers=headers)
    assert integrations.status_code == 200
    assert any(item["id"] == "jira" for item in integrations.json()["integrations"])

    update = client.patch(
        "/api/admin/integrations/jira",
        json={"enabled": True, "status": "Aktif"},
        headers=headers,
    )
    assert update.status_code == 200
    assert any(item["id"] == "jira" and item["enabled"] for item in update.json()["integrations"])


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


def test_support_specialist_can_only_manage_ticket_queue():
    admin_headers = auth_headers()
    create = client.post(
        "/api/tickets",
        json={"message": "Kargo teslimat sorunu için temsilci desteği lazım", "priority": "normal"},
        headers=admin_headers,
    )
    assert create.status_code == 200
    ticket = create.json()

    support_username = f"support_{uuid4().hex[:8]}"
    support_create = client.post(
        "/api/admin/users",
        json={"username": support_username, "password": "secret123", "role": "support"},
        headers=admin_headers,
    )
    assert support_create.status_code == 200
    support_headers = auth_headers(support_username, "secret123")
    queue = client.get("/api/support/tickets", headers=support_headers)
    assert queue.status_code == 200
    assert any(item["id"] == ticket["id"] for item in queue.json()["tickets"])

    update = client.patch(
        f"/api/support/tickets/{ticket['id']}",
        json={"status": "in_progress"},
        headers=support_headers,
    )
    assert update.status_code == 200
    assert update.json()["assignee"] == support_username

    resolved = client.patch(
        f"/api/support/tickets/{ticket['id']}",
        json={"status": "resolved", "resolution_note": "Teslimat kaydı kontrol edildi ve destek ekibi bilgilendirildi."},
        headers=support_headers,
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert "Teslimat kaydı" in resolved.json()["resolution_note"]
    assert resolved.json()["resolution_minutes"] is not None
    assert resolved.json()["resolution_score"] >= 85

    reopened = client.post(
        f"/api/tickets/{ticket['id']}/reopen",
        json={"reason": "Çalışan sorunun devam ettiğini belirtti."},
        headers=support_headers,
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "open"
    assert reopened.json()["resolution_score"] is None

    blocked = client.get("/api/admin/users", headers=support_headers)
    assert blocked.status_code == 403


def test_admin_export_and_escalations_are_available():
    headers = auth_headers()
    create = client.post(
        "/api/tickets",
        json={"message": "KVKK konusu uzman onayi gerektiriyor", "priority": "normal"},
        headers=headers,
    )
    assert create.status_code == 200

    escalations = client.get("/api/admin/escalations", headers=headers)
    assert escalations.status_code == 200
    assert any(item["id"] == create.json()["id"] for item in escalations.json()["tickets"])

    export = client.get("/api/admin/export", headers=headers)
    assert export.status_code == 200
    payload = export.json()
    assert payload["metadata"]["format"] == "json"
    assert payload["users"]
    assert payload["tickets"]


def test_employee_can_see_only_own_tickets():
    username = f"employee_{uuid4().hex[:8]}"
    create_user = client.post(
        "/api/admin/users",
        json={"username": username, "password": "secret123", "role": "employee"},
        headers=auth_headers(),
    )
    assert create_user.status_code == 200
    user_headers = auth_headers(username, "secret123")

    create_ticket = client.post(
        "/api/tickets",
        json={"message": "VPN erişim sorunum var", "priority": "normal", "requester": "someone_else"},
        headers=user_headers,
    )
    assert create_ticket.status_code == 200
    ticket = create_ticket.json()
    assert ticket["requester"] == username

    mine = client.get("/api/tickets/me", headers=user_headers)
    assert mine.status_code == 200
    assert [item["id"] for item in mine.json()["tickets"]] == [ticket["id"]]

    admin_list = client.get("/api/admin/tickets", headers=user_headers)
    assert admin_list.status_code == 403


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
