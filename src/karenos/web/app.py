"""Secure FastAPI web application for browser-based KAREN OS."""

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
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, field_validator

load_dotenv()
logger = logging.getLogger("karenos.web")

STATIC_DIR = Path(__file__).parent / "static"
app = FastAPI(
    title="KAREN OS",
    description="Browser interface for the KAREN OS personal assistant.",
    version="0.2.0",
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


def _environment() -> tuple[str, str, str]:
    api_key = os.getenv("KAREN_AI_API_KEY", "").strip()
    model = os.getenv("KAREN_AI_MODEL", "").strip()
    access_password = os.getenv("KAREN_ACCESS_PASSWORD", "").strip()
    return api_key, model, access_password


def _require_access(provided_code: str | None) -> None:
    _, _, expected_code = _environment()
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


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=()"
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
    api_key, model, access_password = _environment()
    return {
        "application": "KAREN OS",
        "ai_ready": bool(api_key and model),
        "access_protected": bool(access_password),
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

    api_key, model, _ = _environment()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="The app owner has not configured the AI API key on the hosting service.",
        )
    if not model:
        raise HTTPException(
            status_code=503,
            detail="The app owner has not configured KAREN_AI_MODEL on the hosting service.",
        )
    if payload.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="The last message must be from the user.")

    conversation = [
        {"role": message.role, "content": message.content}
        for message in payload.messages
    ]
    client = AsyncOpenAI(api_key=api_key)
    try:
        result = await client.responses.create(
            model=model,
            instructions=(
                "You are KAREN, a capable personal AI assistant. Be helpful, clear, and "
                "accurate. Admit uncertainty. Never claim to have accessed a device, "
                "camera, file, account, or external service unless an available tool "
                "actually performed that action. Ask before consequential actions."
            ),
            input=conversation,
            max_output_tokens=900,
        )
        answer = result.output_text.strip()
        if not answer:
            answer = "I couldn't produce a text response. Please try again."
        return {"reply": answer}
    except Exception as exc:
        logger.exception("AI provider request failed")
        raise HTTPException(
            status_code=502,
            detail="The AI provider request failed. Check the server configuration and logs.",
        ) from exc
    finally:
        await client.close()
