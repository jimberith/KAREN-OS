import asyncio

from fastapi.testclient import TestClient

import karenos.web.app as web_app
from karenos.web.features.memory import MemoryStore

client = TestClient(web_app.app)


def test_status_lists_v04_capabilities(monkeypatch):
    monkeypatch.setenv("KAREN_AI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    response = client.get("/api/status")
    assert response.status_code == 200
    features = response.json()["features"]
    assert features["persistent_memory"] is True
    assert features["image_analysis"] is True
    assert features["local_device_agent"] is True


def test_natural_language_device_command_returns_confirmation_card(monkeypatch):
    monkeypatch.setenv("KAREN_REQUIRE_ACCESS_CODE", "false")
    response = client.post(
        "/api/chat",
        json={
            "session_id": "default",
            "messages": [{"role": "user", "content": "Open YouTube"}],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "automation"
    assert data["action"]["requires_confirmation"] is True
    assert data["action"]["target"] == "youtube"


def test_remember_and_recall_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("KAREN_REQUIRE_ACCESS_CODE", "false")
    original = web_app.memory
    web_app.memory = MemoryStore(tmp_path / "chat.sqlite3")
    try:
        saved = client.post(
            "/api/chat",
            json={
                "session_id": "default",
                "messages": [{"role": "user", "content": "Remember that my robot is named KAREN"}],
            },
        )
        assert saved.status_code == 200
        assert "saved" in saved.json()["reply"].lower()

        recalled = client.post(
            "/api/chat",
            json={
                "session_id": "default",
                "messages": [{"role": "user", "content": "What do you remember?"}],
            },
        )
        assert recalled.status_code == 200
        assert "robot is named KAREN" in recalled.json()["reply"]
    finally:
        web_app.memory = original


def test_memory_endpoints_require_public_access_code(monkeypatch):
    monkeypatch.setenv("KAREN_REQUIRE_ACCESS_CODE", "true")
    monkeypatch.setenv("KAREN_ACCESS_PASSWORD", "example-password")
    response = client.get("/api/memory?session_id=default")
    assert response.status_code == 401


def test_web_search_returns_source_links_without_ai_key(monkeypatch):
    monkeypatch.setenv("KAREN_REQUIRE_ACCESS_CODE", "false")
    monkeypatch.delenv("KAREN_AI_API_KEY", raising=False)
    monkeypatch.delenv("KAREN_AI_MODEL", raising=False)

    async def fake_search(query, limit=5):
        return [{
            "title": "Example current source",
            "url": "https://example.com/news",
            "snippet": "An indexed result."
        }]

    monkeypatch.setattr(web_app, "search_web", fake_search)
    response = client.post(
        "/api/chat",
        json={
            "session_id": "default",
            "messages": [{"role": "user", "content": "Search the web for latest AI news"}],
        },
    )
    assert response.status_code == 200
    assert response.json()["sources"][0]["url"] == "https://example.com/news"
