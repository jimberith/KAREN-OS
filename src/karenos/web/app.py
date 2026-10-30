"""Browser application backend for KAREN OS."""

from __future__ import annotations

import logging
import os
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Literal

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
    version="0.3.1",
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


def _provider_error_message(exc: Exception) -> str:
    """Return actionable provider errors without exposing credentials or raw request data."""
    if isinstance(exc, AuthenticationError):
        return (
            "The AI provider rejected the API key. Check KAREN_AI_API_KEY and confirm that "
            "the key belongs to the provider selected by KAREN_AI_BASE_URL."
        )
    if isinstance(exc, PermissionDeniedError):
        return (
            "The API key or project does not have permission to use this model. Check "
            "KAREN_AI_MODEL and the model access settings for your provider account."
        )
    if isinstance(exc, NotFoundError):
        return (
            "The AI provider could not find the configured model. Check KAREN_AI_MODEL "
            "against the provider's current model catalogue."
        )
    if isinstance(exc, RateLimitError):
        code = str(getattr(exc, "code", "") or "").lower()
        if code in {"insufficient_quota", "credit_balance_exhausted"}:
            return (
                "The AI provider account has no available credit or has reached a spend "
                "limit. Check provider billing, project budget, and usage limits."
            )
        return (
            "The AI provider rate limit was reached. Wait briefly and try again, or review "
            "the provider account's request and token limits."
        )
    if isinstance(exc, APIConnectionError):
        return "KAREN OS could not connect to the configured AI provider. Check the network."
    if isinstance(exc, APIStatusError):
        status = getattr(exc, "status_code", "unknown")
        return (
            f"The AI provider returned HTTP {status}. Check the API endpoint, selected "
            "model, key permissions, and the Codespaces terminal log."
        )
    return (
        "The AI provider request failed unexpectedly. Check the Codespaces terminal log "
        "for the exception type and try again."
    )


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
    api_key, model, access_password, base_url = _environment()
    return {
        "application": "KAREN OS",
        "ai_ready": bool(api_key and model and base_url),
        "access_protected": _access_code_required(),
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

    conversation = [
        {
            "role": "system",
            "content": (
                "You are KAREN, a practical personal AI assistant inspired by a capable "
                "science-fiction assistant. Be helpful, concise, clear, and accurate. "
                "Admit uncertainty. Never claim to have accessed a device, camera, file, "
                "account, or external service unless an available tool actually performed "
                "that action. Ask before consequential actions."
            ),
        },
        *[
            {"role": message.role, "content": message.content}
            for message in payload.messages
        ],
    ]

    # Chat Completions is supported by OpenAI and the OpenAI-compatible APIs
    # offered by Gemini, Groq, and OpenRouter.
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url.rstrip("/") + "/",
        timeout=60.0,
        max_retries=0,
    )
    try:
        result = await client.chat.completions.create(
            model=model,
            messages=conversation,
        )
        answer = result.choices[0].message.content
        if not answer:
            answer = "I couldn't produce a text response. Please try again."
        return {"reply": answer.strip()}
    except Exception as exc:
        logger.exception("AI provider request failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=502, detail=_provider_error_message(exc)) from exc
    finally:
        await client.close()
