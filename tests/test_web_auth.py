from fastapi.testclient import TestClient

from karenos.web.app import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_status_does_not_expose_credentials(monkeypatch):
    monkeypatch.setenv("KAREN_AI_API_KEY", "test-secret-value")
    monkeypatch.setenv("KAREN_AI_MODEL", "test-model")
    monkeypatch.setenv("KAREN_ACCESS_PASSWORD", "test-access-code")

    response = client.get("/api/status")

    assert response.status_code == 200
    assert response.json()["ai_ready"] is True
    assert "test-secret-value" not in response.text
    assert "test-access-code" not in response.text


def test_chat_requires_access_code(monkeypatch):
    monkeypatch.setenv("KAREN_ACCESS_PASSWORD", "correct-code")

    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Hello"}]},
        headers={"X-Karen-Access-Code": "wrong-code"},
    )

    assert response.status_code == 401


def test_access_check_accepts_configured_code(monkeypatch):
    monkeypatch.setenv("KAREN_ACCESS_PASSWORD", "correct-code")

    response = client.post(
        "/api/auth/check",
        headers={"X-Karen-Access-Code": "correct-code"},
    )

    assert response.status_code == 200
    assert response.json()["authorized"] is True


def test_chat_rejects_when_api_key_missing(monkeypatch):
    monkeypatch.setenv("KAREN_ACCESS_PASSWORD", "correct-code")
    monkeypatch.delenv("KAREN_AI_API_KEY", raising=False)
    monkeypatch.setenv("KAREN_AI_MODEL", "test-model")

    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Hello"}]},
        headers={"X-Karen-Access-Code": "correct-code"},
    )

    assert response.status_code == 503
