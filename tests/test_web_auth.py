from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient

import karenos.web.app as web_app

client = TestClient(web_app.app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_status_does_not_expose_credentials(monkeypatch):
    monkeypatch.setenv("KAREN_AI_API_KEY", "test-secret-value")
    monkeypatch.setenv("KAREN_AI_MODEL", "test-model")
    monkeypatch.setenv("KAREN_ACCESS_PASSWORD", "test-access-code")
    monkeypatch.setenv("KAREN_AI_BASE_URL", "https://test.invalid/v1")
    monkeypatch.setenv("KAREN_REQUIRE_ACCESS_CODE", "true")

    response = client.get("/api/status")

    assert response.status_code == 200
    assert response.json()["ai_ready"] is True
    assert response.json()["access_protected"] is True
    assert response.json()["provider_host"] == "test.invalid"
    assert response.json()["model"] == "test-model"
    assert response.json()["api_key_configured"] is True
    assert "test-secret-value" not in response.text
    assert "test-access-code" not in response.text


def test_codespaces_mode_does_not_require_second_login(monkeypatch):
    monkeypatch.setenv("KAREN_ACCESS_PASSWORD", "unused-password")
    monkeypatch.setenv("KAREN_REQUIRE_ACCESS_CODE", "false")

    response = client.get("/api/status")
    access = client.post("/api/auth/check")

    assert response.status_code == 200
    assert response.json()["access_protected"] is False
    assert access.status_code == 200
    assert access.json()["authorized"] is True


def test_chat_requires_access_code_when_explicitly_enabled(monkeypatch):
    monkeypatch.setenv("KAREN_ACCESS_PASSWORD", "correct-code")
    monkeypatch.setenv("KAREN_REQUIRE_ACCESS_CODE", "true")

    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Hello"}]},
        headers={"X-Karen-Access-Code": "wrong-code"},
    )

    assert response.status_code == 401


def test_access_check_accepts_configured_code(monkeypatch):
    monkeypatch.setenv("KAREN_ACCESS_PASSWORD", "correct-code")
    monkeypatch.setenv("KAREN_REQUIRE_ACCESS_CODE", "true")

    response = client.post(
        "/api/auth/check",
        headers={"X-Karen-Access-Code": "correct-code"},
    )

    assert response.status_code == 200
    assert response.json()["authorized"] is True


def test_chat_rejects_when_api_key_missing(monkeypatch):
    monkeypatch.setenv("KAREN_REQUIRE_ACCESS_CODE", "false")
    monkeypatch.delenv("KAREN_AI_API_KEY", raising=False)
    monkeypatch.setenv("KAREN_AI_MODEL", "test-model")
    monkeypatch.setenv("KAREN_AI_BASE_URL", "https://test.invalid/v1")

    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )

    assert response.status_code == 503


def test_chat_uses_configured_openai_compatible_provider(monkeypatch):
    monkeypatch.setenv("KAREN_REQUIRE_ACCESS_CODE", "false")
    monkeypatch.setenv("KAREN_AI_API_KEY", "provider-test-key")
    monkeypatch.setenv("KAREN_AI_MODEL", "openai-test-model")
    monkeypatch.setenv("KAREN_AI_BASE_URL", "https://api.groq.com/openai/v1")
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured["request"] = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Hello from test."))]
            )

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

        async def close(self):
            return None

    monkeypatch.setattr(web_app, "AsyncOpenAI", FakeClient)
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Hello KAREN"}]},
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "Hello from test."
    assert captured["client"]["api_key"] == "provider-test-key"
    assert captured["client"]["base_url"] == "https://api.groq.com/openai/v1/"
    assert captured["request"]["model"] == "openai-test-model"
    assert captured["request"]["messages"][-1] == {
        "role": "user",
        "content": "Hello KAREN",
    }


def test_gemini_uses_native_api_key_header(monkeypatch):
    monkeypatch.setenv("KAREN_REQUIRE_ACCESS_CODE", "false")
    monkeypatch.setenv("KAREN_AI_API_KEY", "gemini-test-key")
    monkeypatch.setenv("KAREN_AI_MODEL", "gemini-3.8-flash")
    monkeypatch.setenv(
        "KAREN_AI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    captured = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "candidates": [{
                    "content": {"parts": [{"text": "Hello from native Gemini."}]}
                }]
            }

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = json
            return FakeResponse()

    monkeypatch.setattr(web_app.httpx, "AsyncClient", FakeAsyncClient)
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Hello KAREN"}]},
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "Hello from native Gemini."
    assert captured["headers"]["x-goog-api-key"] == "gemini-test-key"
    assert captured["url"].endswith("/models/gemini-3.8-flash:generateContent")
    assert captured["body"]["contents"][0]["role"] == "user"


def test_chat_rejects_when_last_message_is_not_user(monkeypatch):
    monkeypatch.setenv("KAREN_REQUIRE_ACCESS_CODE", "false")
    monkeypatch.setenv("KAREN_AI_API_KEY", "provider-test-key")
    monkeypatch.setenv("KAREN_AI_MODEL", "test-model")
    monkeypatch.setenv("KAREN_AI_BASE_URL", "https://test.invalid/v1")
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "assistant", "content": "Hello"}]},
    )
    assert response.status_code == 400



def test_gemini_diagnostics_accepts_model_and_key(monkeypatch):
    monkeypatch.setenv("KAREN_AI_API_KEY", "gemini-test-key")
    monkeypatch.setenv("KAREN_AI_MODEL", "gemini-3.8-flash")
    monkeypatch.setenv(
        "KAREN_AI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    class FakeResponse:
        is_success = True

        def json(self):
            return {"name": "models/gemini-3.8-flash"}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, headers):
            assert url.endswith("/v1beta/models/gemini-3.8-flash")
            assert headers["x-goog-api-key"] == "gemini-test-key"
            return FakeResponse()

    monkeypatch.setattr(web_app.httpx, "AsyncClient", FakeAsyncClient)
    response = client.get("/api/diagnostics")

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["stage"] == "ready"
    assert "gemini-test-key" not in response.text


def test_gemini_diagnostics_reports_auth_failure(monkeypatch):
    monkeypatch.setenv("KAREN_AI_API_KEY", "bad-test-key")
    monkeypatch.setenv("KAREN_AI_MODEL", "gemini-3.8-flash")
    monkeypatch.setenv(
        "KAREN_AI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    class FakeResponse:
        is_success = False
        status_code = 400

        def json(self):
            return {"error": {"message": "API key not valid", "status": "INVALID_ARGUMENT"}}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, headers):
            return FakeResponse()

    monkeypatch.setattr(web_app.httpx, "AsyncClient", FakeAsyncClient)
    response = client.get("/api/diagnostics")

    assert response.status_code == 200
    assert response.json()["stage"] == "authentication"
    assert response.json()["http_status"] == 400
    assert "bad-test-key" not in response.text


def test_gemini_retries_503_then_succeeds(monkeypatch):
    monkeypatch.setenv("KAREN_REQUIRE_ACCESS_CODE", "false")
    monkeypatch.setenv("KAREN_AI_API_KEY", "gemini-test-key")
    monkeypatch.setenv("KAREN_AI_MODEL", "gemini-3.8-flash")
    monkeypatch.setenv("KAREN_GEMINI_FALLBACK_MODELS", "")
    monkeypatch.setenv(
        "KAREN_AI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    captured = {"attempts": 0}

    class FakeResponse:
        def __init__(self, status_code):
            self.status_code = status_code
            self.request = httpx.Request("POST", "https://example.test")

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "temporary overload", request=self.request,
                    response=httpx.Response(self.status_code, request=self.request),
                )

        def json(self):
            return {"candidates": [{
                "content": {"parts": [{"text": "Recovered after retry."}]}
            }]}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            captured["attempts"] += 1
            return FakeResponse(503 if captured["attempts"] < 3 else 200)

    async def no_wait(_seconds):
        return None

    monkeypatch.setattr(web_app.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(web_app.asyncio, "sleep", no_wait)
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "Recovered after retry."
    assert captured["attempts"] == 2


def test_gemini_falls_back_after_primary_model_503(monkeypatch):
    monkeypatch.setenv("KAREN_REQUIRE_ACCESS_CODE", "false")
    monkeypatch.setenv("KAREN_AI_API_KEY", "gemini-test-key")
    monkeypatch.setenv("KAREN_AI_MODEL", "gemini-3.8-flash")
    monkeypatch.setenv("KAREN_GEMINI_FALLBACK_MODELS", "gemini-3.7-flash")
    monkeypatch.setenv(
        "KAREN_AI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    seen_models = []

    class FakeResponse:
        def __init__(self, status_code, model_name):
            self.status_code = status_code
            self.model_name = model_name
            self.request = httpx.Request("POST", "https://example.test")

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "temporary overload", request=self.request,
                    response=httpx.Response(self.status_code, request=self.request),
                )

        def json(self):
            return {"candidates": [{
                "content": {"parts": [{"text": f"Answered by {self.model_name}"}]}
            }]}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            model_name = url.split("/models/")[1].split(":")[0]
            seen_models.append(model_name)
            return FakeResponse(503 if model_name == "gemini-3.8-flash" else 200, model_name)

    async def no_wait(_seconds):
        return None

    monkeypatch.setattr(web_app.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(web_app.asyncio, "sleep", no_wait)
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "Answered by gemini-3.7-flash"
    assert seen_models == ["gemini-3.8-flash"] * 2 + ["gemini-3.7-flash"]


def test_gemini_timeout_switches_to_fast_fallback(monkeypatch):
    monkeypatch.setenv("KAREN_REQUIRE_ACCESS_CODE", "false")
    monkeypatch.setenv("KAREN_AI_API_KEY", "gemini-test-key")
    monkeypatch.setenv("KAREN_AI_MODEL", "gemini-3.8-flash")
    monkeypatch.setenv("KAREN_GEMINI_FALLBACK_MODELS", "gemini-3.5-flash-lite")
    monkeypatch.setenv(
        "KAREN_AI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    attempted_models = []

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"candidates": [{
                "content": {"parts": [{"text": "Fallback model answered."}]}
            }]}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            assert kwargs["timeout"].read == 20.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            model_name = url.split("/models/")[1].split(":")[0]
            attempted_models.append(model_name)
            if model_name == "gemini-3.8-flash":
                raise httpx.ReadTimeout("model response timed out")
            return FakeResponse()

    monkeypatch.setattr(web_app.httpx, "AsyncClient", FakeAsyncClient)
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "Fallback model answered."
    assert attempted_models == ["gemini-3.8-flash", "gemini-3.5-flash-lite"]


def test_gemini_timeout_has_actionable_error_when_all_models_time_out(monkeypatch):
    monkeypatch.setenv("KAREN_REQUIRE_ACCESS_CODE", "false")
    monkeypatch.setenv("KAREN_AI_API_KEY", "gemini-test-key")
    monkeypatch.setenv("KAREN_AI_MODEL", "gemini-3.8-flash")
    monkeypatch.setenv("KAREN_GEMINI_FALLBACK_MODELS", "gemini-3.5-flash-lite")
    monkeypatch.setenv(
        "KAREN_AI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            raise httpx.ReadTimeout("test timeout")

    monkeypatch.setattr(web_app.httpx, "AsyncClient", FakeAsyncClient)
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )

    assert response.status_code == 502
    assert "did not respond within the request timeout" in response.json()["detail"]
