import asyncio
import base64

import httpx
import pytest

import karenos.web.features.gemini as gemini


def test_gemini_tts_saves_generated_wav(monkeypatch, tmp_path):
    audio_bytes = b"RIFF-test-wave-data"
    captured = {}

    class FakeResponse:
        status_code = 200
        is_success = True

        def json(self):
            return {
                "steps": [{
                    "type": "model_output",
                    "content": [{
                        "type": "audio",
                        "mime_type": "audio/wav",
                        "data": base64.b64encode(audio_bytes).decode("ascii"),
                    }],
                }]
            }

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured["timeout"] = kwargs["timeout"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = json
            return FakeResponse()

    monkeypatch.setattr(gemini.httpx, "AsyncClient", FakeAsyncClient)
    filename, mime = asyncio.run(
        gemini.generate_speech(
            "test-secret",
            "Hello KAREN",
            tmp_path,
            model="gemini-3.8-flash-lite-tts",
            voice="Kore",
        )
    )

    assert mime == "audio/wav"
    assert (tmp_path / filename).read_bytes() == audio_bytes
    assert captured["url"].endswith("/v1beta/interactions")
    assert captured["headers"]["x-goog-api-key"] == "test-secret"
    assert captured["body"]["model"] == "gemini-3.8-flash-lite-tts"
    assert captured["body"]["generation_config"]["speech_config"][0]["voice"] == "Kore"


def test_gemini_image_generation_uses_v1_model_endpoint(monkeypatch, tmp_path):
    image_bytes = b"fake-png-data"
    captured = {}

    class FakeResponse:
        status_code = 200
        is_success = True

        def json(self):
            return {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": base64.b64encode(image_bytes).decode("ascii"),
                            }
                        }]
                    }
                }]
            }

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["payload"] = json
            return FakeResponse()

    monkeypatch.setattr(gemini.httpx, "AsyncClient", FakeAsyncClient)
    filename, mime = asyncio.run(
        gemini.generate_image(
            "test-key",
            "A small robot assistant",
            tmp_path,
            model="gemini-3.1-flash-image",
        )
    )

    assert mime == "image/png"
    assert (tmp_path / filename).read_bytes() == image_bytes
    assert captured["url"].endswith("/v1/models/gemini-3.1-flash-image:generateContent")
    assert captured["headers"]["x-goog-api-key"] == "test-key"
    assert captured["payload"]["generationConfig"]["responseModalities"] == ["IMAGE"]


def test_gemini_tts_rejects_empty_text(tmp_path):
    with pytest.raises(gemini.GeminiServiceError, match="no text"):
        asyncio.run(gemini.generate_speech("test-key", "  ", tmp_path))
