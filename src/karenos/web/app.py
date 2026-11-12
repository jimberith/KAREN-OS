"""Browser application backend for KAREN OS."""

from __future__ import annotations

import asyncio
import logging
import os
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Literal
from urllib.parse import quote, urlsplit

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import (
    APIConnectionError,
    APIStatusError,
    AsyncOpenAI,
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
from pydantic import BaseModel, Field, field_validator

load_dotenv()
logger = logging.getLogger("karenos.web")

STATIC_DIR = Path(__file__).parent / "static"
app = FastAPI(
    title="KAREN OS",
    description="Browser interface for the KAREN OS personal assistant.",
    version="0.3.2",
    docs_url=None,
    redoc_url=None,
)
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

_RATE_LIMIT = 18
_RATE_WINDOW_SECONDS = 60
_requests: dict[str, deque[float]] = defaultdict(deque)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank.")
        return value


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)


def _environment() -> tuple[str, str, str, str]:
    api_key = os.getenv("KAREN_AI_API_KEY", "").strip()
    model = os.getenv("KAREN_AI_MODEL", "").strip()
    access_password = os.getenv("KAREN_ACCESS_PASSWORD", "").strip()
    base_url = os.getenv("KAREN_AI_BASE_URL", "https://api.openai.com/v1").strip()
    return api_key, model, access_password, base_url


def _access_code_required() -> bool:
    """App password is opt-in; private Codespaces ports rely on GitHub access control."""
    return os.getenv("KAREN_REQUIRE_ACCESS_CODE", "false").strip().lower() in {
        "1", "true", "yes"
    }


def _require_access(provided_code: str | None) -> None:
    if not _access_code_required():
        return
    _, _, expected_code, _ = _environment()
    if not expected_code:
        raise HTTPException(
            status_code=503,
            detail="The app owner must configure KAREN_ACCESS_PASSWORD on the hosting service.",
        )
    if not provided_code or not secrets.compare_digest(provided_code, expected_code):
        raise HTTPException(status_code=401, detail="Access code is incorrect.")


def _check_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    timestamps = _requests[client_ip]
    while timestamps and now - timestamps[0] > _RATE_WINDOW_SECONDS:
        timestamps.popleft()
    if len(timestamps) >= _RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many messages in a short period. Wait a minute and try again.",
        )
    timestamps.append(now)


def _provider_error_message(exc: Exception, base_url: str = "") -> str:
    """Return actionable provider errors without exposing credentials or raw request data."""
    provider_host = (urlsplit(base_url).hostname or "").lower()
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        try:
            body = exc.response.json()
            google_message = body.get("error", {}).get("message", "")
        except (ValueError, AttributeError):
            google_message = ""
        if provider_host == "generativelanguage.googleapis.com":
            if status_code == 503:
                return (
                    "Gemini is temporarily overloaded. KAREN retried the request and tried "
                    "its fallback models. Wait a little and try again; this is not an API-key error."
                )
            if status_code == 401:
                return (
                    "Gemini rejected the key. KAREN_AI_API_KEY must be a Gemini API key "
                    "created in Google AI Studio, not an OpenAI key. Re-copy the complete "
                    "key into GitHub Codespaces Secrets and restart the Codespace."
                )
            if status_code == 403:
                return (
                    "Gemini denied access to this project or API key. Check that the "
                    "Generative Language API is enabled and the key is permitted to use it."
                )
            if status_code == 404:
                return (
                    "Gemini could not find this model. Check KAREN_AI_MODEL in the current "
                    "Google AI Studio model list."
                )
            if status_code == 429:
                return (
                    "Gemini quota or rate limit reached. Check Google AI Studio usage and "
                    "wait for the quota window to reset."
                )
            if status_code >= 500:
                return (
                    f"Gemini returned HTTP {status_code}. This may be temporary; wait briefly "
                    "and retry."
                )
        return f"The AI provider returned HTTP {status_code}. {google_message[:240]}"
    if isinstance(exc, AuthenticationError):
        if provider_host == "generativelanguage.googleapis.com":
            return (
                "Gemini rejected the API key. Use a Gemini key from Google AI Studio, "
                "not an OpenAI key."
            )
        if provider_host == "api.groq.com":
            return "Groq rejected the key. Use a key created in the Groq Console."
        if provider_host == "openrouter.ai":
            return "OpenRouter rejected the key. Use a key created in OpenRouter."
        return "The AI provider rejected the API key. Check that the key matches the provider."
    if isinstance(exc, PermissionDeniedError):
        return "The API key or project does not have permission to use this model."
    if isinstance(exc, NotFoundError):
        return "The AI provider could not find the configured model. Check KAREN_AI_MODEL."
    if isinstance(exc, RateLimitError):
        code = str(getattr(exc, "code", "") or "").lower()
        if code in {"insufficient_quota", "credit_balance_exhausted"}:
            return "The AI provider account has no available credit or has reached its spend limit."
        return "The AI provider rate limit was reached. Wait briefly and try again."
    if isinstance(exc, APIConnectionError):
        return "KAREN OS could not connect to the configured AI provider. Check the network."
    if isinstance(exc, APIStatusError):
        return f"The AI provider returned HTTP {exc.status_code}. Check model and key permissions."
    if isinstance(exc, httpx.RequestError):
        return "KAREN OS could not reach the Gemini API. Check the Codespaces network."
    return "The AI provider request failed. Check the Codespaces terminal for the exception type."


SYSTEM_PROMPT = (
    "You are KAREN, a practical personal AI assistant inspired by a capable science-fiction "
    "assistant. Be helpful, concise, clear, and accurate. Admit uncertainty. Never claim to "
    "have accessed a device, camera, file, account, or external service unless an available "
    "tool actually performed that action. Ask before consequential actions."
)



async def _gemini_reply(api_key: str, model: str, messages: list[ChatMessage]) -> str:
    """Call Gemini natively, retry transient overloads, then try stable fallback models."""
    contents = [
        {
            "role": "user" if message.role == "user" else "model",
            "parts": [{"text": message.content}],
        }
        for message in messages
    ]
    configured_fallbacks = os.getenv(
        "KAREN_GEMINI_FALLBACK_MODELS",
        "gemini-3.7-flash,gemini-3.6-flash",
    )
    fallback_models = [
        item.strip()
        for item in configured_fallbacks.split(",")
        if item.strip() and item.strip() != model
    ]
    models_to_try = [model, *fallback_models]
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 900, "temperature": 0.7},
    }
    last_overload: httpx.Response | None = None

    async with httpx.AsyncClient(timeout=60.0) as client:
        for candidate_model in models_to_try:
            model_path = quote(candidate_model, safe="-_.")
            url = (
                "https://generativelanguage.googleapis.com/v1beta/"
                f"models/{model_path}:generateContent"
            )
            for attempt in range(3):
                response = await client.post(
                    url,
                    headers={
                        "x-goog-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                    json=body,
                )

                if response.status_code == 503:
                    last_overload = response
                    if attempt < 2:
                        await asyncio.sleep(1.0 * (2 ** attempt))
                        continue
                    logger.warning(
                        "Gemini model %s remained unavailable after retries; trying fallback",
                        candidate_model,
                    )
                    break

                response.raise_for_status()
                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    feedback = data.get("promptFeedback", {}).get("blockReason", "")
                    if feedback:
                        return f"Gemini blocked this prompt for safety reasons ({feedback})."
                    return "Gemini returned no response. Please try a different prompt."

                parts = candidates[0].get("content", {}).get("parts", [])
                answer = "\\n".join(
                    part.get("text", "")
                    for part in parts
                    if isinstance(part.get("text"), str)
                ).strip()
                if candidate_model != model:
                    logger.info("Gemini fallback model %s handled the request", candidate_model)
                return answer or "Gemini returned no text response. Please try again."

    if last_overload is not None:
        raise httpx.HTTPStatusError(
            "Gemini remained unavailable after retrying configured fallback models.",
            request=last_overload.request,
            response=last_overload,
        )
    return "Gemini could not complete the request. Please try again."


async def _compatible_reply(
    api_key: str, model: str, base_url: str, messages: list[dict[str, str]]
) -> str:
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url.rstrip("/") + "/",
        timeout=60.0,
        max_retries=0,
    )
    try:
        result = await client.chat.completions.create(model=model, messages=messages)
        answer = result.choices[0].message.content
        return answer.strip() if answer else "The AI provider returned an empty response."
    finally:
        await client.close()


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(self)"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "karen-os"}


@app.get("/api/status")
async def status() -> dict[str, object]:
    api_key, model, _, base_url = _environment()
    provider_host = urlsplit(base_url).hostname or "not-configured"
    provider_name = {
        "generativelanguage.googleapis.com": "Gemini",
        "api.groq.com": "Groq",
        "openrouter.ai": "OpenRouter",
        "api.openai.com": "OpenAI",
    }.get(provider_host, provider_host)
    return {
        "application": "KAREN OS",
        "ai_ready": bool(api_key and model and base_url),
        "api_key_configured": bool(api_key),
        "provider_host": provider_host,
        "provider_name": provider_name,
        "model": model or "not-configured",
        "access_protected": _access_code_required(),
    }




@app.get("/api/diagnostics")
async def diagnostics() -> dict[str, object]:
    """Check provider reachability, API key authentication, and model availability."""
    api_key, model, _, base_url = _environment()
    provider_host = (urlsplit(base_url).hostname or "").lower()

    if not api_key:
        return {
            "ok": False,
            "stage": "configuration",
            "message": "KAREN_AI_API_KEY is missing.",
        }
    if not model:
        return {
            "ok": False,
            "stage": "configuration",
            "message": "KAREN_AI_MODEL is missing.",
        }

    if provider_host == "generativelanguage.googleapis.com":
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{quote(model, safe='-_.')}"
        )
        headers = {"x-goog-api-key": api_key}
    else:
        return {
            "ok": False,
            "stage": "provider",
            "provider_host": provider_host or "not-configured",
            "message": (
                "This diagnostic endpoint currently checks Gemini native API credentials. "
                "For another provider, use its own model-list or account diagnostic."
            ),
        }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
    except httpx.ConnectTimeout:
        return {
            "ok": False,
            "stage": "network",
            "provider_host": provider_host,
            "message": "Connection to Google timed out. Retry or test the endpoint from the Codespaces terminal.",
        }
    except httpx.ReadTimeout:
        return {
            "ok": False,
            "stage": "network",
            "provider_host": provider_host,
            "message": "Google did not respond before the diagnostic timeout.",
        }
    except httpx.ConnectError as exc:
        cause = str(exc.__cause__ or exc)
        dns_problem = "name or service not known" in cause.lower() or "temporary failure in name resolution" in cause.lower() or "getaddrinfo" in cause.lower()
        return {
            "ok": False,
            "stage": "dns" if dns_problem else "network",
            "provider_host": provider_host,
            "error_type": type(exc).__name__,
            "message": (
                "The Codespace could not resolve Google's API hostname. Check DNS/network access."
                if dns_problem
                else "The Codespace could not establish a TLS or TCP connection to Google's API."
            ),
        }
    except httpx.RequestError as exc:
        return {
            "ok": False,
            "stage": "network",
            "provider_host": provider_host,
            "error_type": type(exc).__name__,
            "message": "The request could not reach Google's API. Check the Codespaces network.",
        }

    if response.is_success:
        data = response.json()
        return {
            "ok": True,
            "stage": "ready",
            "provider": "Gemini",
            "provider_host": provider_host,
            "model": data.get("name", f"models/{model}"),
            "message": "Google accepted the API key and the selected model is available.",
        }

    try:
        error_data = response.json().get("error", {})
        provider_message = str(error_data.get("message", "No error message supplied"))[:300]
        provider_status = error_data.get("status", "")
    except (ValueError, AttributeError):
        provider_message = "Google returned a non-JSON error response."
        provider_status = ""

    status_code = response.status_code
    if status_code in {400, 401}:
        hint = "Google rejected the API key. Re-copy a Gemini API key from Google AI Studio."
        stage = "authentication"
    elif status_code == 403:
        hint = "The key was received, but this Google project or key lacks API permission."
        stage = "permission"
    elif status_code == 404:
        hint = "The model was not found. Check KAREN_AI_MODEL against Google's current model list."
        stage = "model"
    elif status_code == 429:
        hint = "Gemini quota or rate limit reached. Check Google AI Studio usage and billing."
        stage = "quota"
    else:
        hint = f"Google returned HTTP {status_code}. Check the provider response below."
        stage = "provider"

    return {
        "ok": False,
        "stage": stage,
        "http_status": status_code,
        "provider_status": provider_status,
        "provider_message": provider_message,
        "hint": hint,
    }


@app.post("/api/auth/check")
async def check_access(
    x_karen_access_code: str | None = Header(default=None),
) -> dict[str, bool]:
    _require_access(x_karen_access_code)
    return {"authorized": True}


@app.post("/api/chat")
async def chat(
    payload: ChatRequest,
    request: Request,
    x_karen_access_code: str | None = Header(default=None),
) -> dict[str, str]:
    _require_access(x_karen_access_code)
    _check_rate_limit(request)

    api_key, model, _, base_url = _environment()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Set KAREN_AI_API_KEY to a key from your chosen AI provider.",
        )
    if not model:
        raise HTTPException(
            status_code=503,
            detail="Set KAREN_AI_MODEL to a model ID supported by your chosen AI provider.",
        )
    if not base_url:
        raise HTTPException(
            status_code=503,
            detail="Set KAREN_AI_BASE_URL to your chosen provider's API endpoint.",
        )
    if payload.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="The last message must be from the user.")

    provider_host = (urlsplit(base_url).hostname or "").lower()
    compatible_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *[{"role": message.role, "content": message.content} for message in payload.messages],
    ]

    try:
        if provider_host == "generativelanguage.googleapis.com":
            answer = await _gemini_reply(api_key, model, payload.messages)
        else:
            answer = await _compatible_reply(api_key, model, base_url, compatible_messages)
        return {"reply": answer}
    except Exception as exc:
        logger.exception("AI provider request failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=502, detail=_provider_error_message(exc, base_url)) from exc
