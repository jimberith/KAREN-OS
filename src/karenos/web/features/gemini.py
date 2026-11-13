"""Native Gemini API helpers for text, image understanding and image generation."""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from pathlib import Path
from urllib.parse import quote

import httpx

logger = logging.getLogger("karenos.web.gemini")
GEMINI_ROOT = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_V1_ROOT = "https://generativelanguage.googleapis.com/v1"


class GeminiServiceError(RuntimeError):
    """Safe error raised when Gemini cannot complete a request."""


def _model_chain(primary: str) -> list[str]:
    fallback = os.getenv(
        "KAREN_GEMINI_FALLBACK_MODELS",
        "gemini-3.5-flash-lite,gemini-3.1-flash-lite",
    )
    return [primary, *[
        model.strip() for model in fallback.split(",")
        if model.strip() and model.strip() != primary
    ]]


async def _generate(
    api_key: str,
    model: str,
    payload: dict,
    *,
    timeout_seconds: float = 20.0,
    fallback: bool = True,
    api_root: str = GEMINI_ROOT,
) -> dict:
    models = _model_chain(model) if fallback else [model]
    last_error: Exception | None = None
    timeout = httpx.Timeout(connect=8.0, read=timeout_seconds, write=12.0, pool=8.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        for candidate in models:
            url = f"{api_root}/models/{quote(candidate, safe='-_.')}:generateContent"
            for attempt in range(2):
                try:
                    response = await client.post(
                        url,
                        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                        json=payload,
                    )
                except httpx.TimeoutException as exc:
                    last_error = exc
                    logger.warning("Gemini model %s timed out; trying next model", candidate)
                    break
                except httpx.RequestError as exc:
                    raise GeminiServiceError(
                        "Could not connect to Gemini. Check the Codespaces internet connection."
                    ) from exc

                if response.status_code == 503:
                    last_error = httpx.HTTPStatusError(
                        "Gemini temporarily unavailable",
                        request=response.request,
                        response=response,
                    )
                    if attempt == 0:
                        await asyncio.sleep(0.6)
                        continue
                    logger.warning("Gemini model %s returned 503; trying next model", candidate)
                    break

                if response.status_code >= 400:
                    try:
                        provider_error = response.json().get("error", {})
                        message = str(provider_error.get("message", ""))[:240]
                    except (ValueError, AttributeError):
                        message = ""
                    raise GeminiServiceError(
                        f"Gemini returned HTTP {response.status_code}. {message}".strip()
                    )
                return response.json()

    if isinstance(last_error, httpx.TimeoutException):
        raise GeminiServiceError(
            "Gemini timed out on the primary and fallback models. Try again shortly."
        ) from last_error
    if isinstance(last_error, httpx.HTTPStatusError):
        raise GeminiServiceError(
            "Gemini is temporarily overloaded on the configured models. Try again shortly."
        ) from last_error
    raise GeminiServiceError("Gemini could not complete the request.")


def _extract_text(data: dict) -> str:
    candidates = data.get("candidates", [])
    if not candidates:
        feedback = data.get("promptFeedback", {}).get("blockReason", "")
        if feedback:
            return f"Gemini blocked this request for safety reasons ({feedback})."
        return "Gemini returned no answer."
    parts = candidates[0].get("content", {}).get("parts", [])
    return "\n".join(
        str(part.get("text", "")) for part in parts if isinstance(part.get("text"), str)
    ).strip() or "Gemini returned no text."


async def generate_text(
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    *,
    search: bool = False,
) -> tuple[str, list[dict[str, str]]]:
    system_text = "\n\n".join(
        message["content"] for message in messages if message.get("role") == "system"
    )
    if not system_text:
        system_text = (
            "You are KAREN, a capable personal AI assistant. Be clear, accurate, helpful "
            "and concise. Admit uncertainty. Never claim to perform actions unless a "
            "connected tool actually did so. Confirm before consequential actions."
        )
    conversation = [message for message in messages if message.get("role") in {"user", "assistant"}]
    contents = [
        {
            "role": "user" if message["role"] == "user" else "model",
            "parts": [{"text": message["content"][-5000:]}],
        }
        for message in conversation[-16:]
    ]
    payload: dict = {
        "systemInstruction": {"parts": [{"text": system_text}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 1000, "temperature": 0.65},
    }
    if search:
        payload["tools"] = [{"google_search": {}}]
    data = await _generate(api_key, model, payload)
    sources: list[dict[str, str]] = []
    metadata = data.get("candidates", [{}])[0].get("groundingMetadata", {})
    for chunk in metadata.get("groundingChunks", []):
        web = chunk.get("web", {})
        url = str(web.get("uri", ""))
        title = str(web.get("title", url))
        if url.startswith(("https://", "http://")):
            sources.append({"title": title, "url": url})
    return _extract_text(data), sources


async def analyze_image(
    api_key: str,
    model: str,
    image_bytes: bytes,
    mime_type: str,
    question: str,
) -> str:
    payload = {
        "systemInstruction": {
            "parts": [{"text": "You are KAREN's visual perception module. Describe only what is visible. Distinguish observations from guesses. Do not identify real people."}]
        },
        "contents": [{
            "role": "user",
            "parts": [
                {"text": question or "Describe this image. Identify important objects, text, layout, and relevant details."},
                {"inlineData": {"mimeType": mime_type, "data": base64.b64encode(image_bytes).decode("ascii")}},
            ],
        }],
        "generationConfig": {"maxOutputTokens": 900, "temperature": 0.3},
    }
    data = await _generate(api_key, model, payload, timeout_seconds=35.0)
    return _extract_text(data)


async def generate_image(
    api_key: str,
    prompt: str,
    output_dir: Path,
    *,
    model: str = "gemini-3.1-flash-image",
) -> tuple[str, str]:
    payload = {
        "contents": [{"parts": [{"text": prompt[:3000]}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    data = await _generate(
        api_key,
        model,
        payload,
        timeout_seconds=70.0,
        fallback=False,
        api_root=GEMINI_V1_ROOT,
    )
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            image_data = part.get("inlineData") or part.get("inline_data")
            if image_data and image_data.get("data"):
                mime = image_data.get("mimeType", "image/png")
                extension = "jpg" if mime == "image/jpeg" else "png"
                output_dir.mkdir(parents=True, exist_ok=True)
                filename = f"karen-{__import__('uuid').uuid4().hex}.{extension}"
                target = output_dir / filename
                target.write_bytes(base64.b64decode(image_data["data"]))
                return filename, mime
    raise GeminiServiceError("The image model returned no image. Try a more specific prompt.")
