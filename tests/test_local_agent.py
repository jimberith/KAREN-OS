from fastapi.testclient import TestClient

from karenos.agent.app import app

client = TestClient(app)


def test_agent_health_does_not_require_token():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["bind"] == "127.0.0.1"


def test_agent_status_requires_token(monkeypatch):
    monkeypatch.setenv("KAREN_LOCAL_AGENT_TOKEN", "local-test-token")
    response = client.get("/api/status")
    assert response.status_code == 401


def test_agent_rejects_unconfirmed_action(monkeypatch):
    monkeypatch.setenv("KAREN_LOCAL_AGENT_TOKEN", "local-test-token")
    response = client.post(
        "/api/actions",
        headers={"X-Karen-Agent-Token": "local-test-token"},
        json={"action": "open_app", "target": "calculator", "confirmed": False},
    )
    assert response.status_code == 400


def test_agent_rejects_unknown_app_target(monkeypatch):
    monkeypatch.setenv("KAREN_LOCAL_AGENT_TOKEN", "local-test-token")
    response = client.post(
        "/api/actions",
        headers={"X-Karen-Agent-Token": "local-test-token"},
        json={"action": "open_app", "target": "arbitrary-shell", "confirmed": True},
    )
    assert response.status_code == 400
