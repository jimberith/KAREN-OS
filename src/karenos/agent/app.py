"""Loopback-only local device agent with allowlisted, confirmation-gated actions."""

from __future__ import annotations

import hmac
import os
import platform
import shutil
import subprocess
import webbrowser
from typing import Literal
from urllib.parse import urlparse

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="KAREN OS Local Agent", docs_url=None, redoc_url=None)

_ALLOWED_ORIGINS = (
    r"^https://[a-zA-Z0-9-]+\.app\.github\.dev$|"
    r"^https://[a-zA-Z0-9-]+\.github\.dev$|"
    r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"
)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Karen-Agent-Token"],
)


@app.middleware("http")
async def private_network_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


class ActionRequest(BaseModel):
    action: Literal["open_app", "open_website", "volume", "system_status"]
    target: str = Field(min_length=1, max_length=40)
    confirmed: bool = False


def _check_token(token: str | None) -> None:
    expected = os.getenv("KAREN_LOCAL_AGENT_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Local agent token is not configured.")
    if not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Local agent token is incorrect.")


def _start_first_available(candidates: list[list[str]]) -> str:
    for command in candidates:
        executable = shutil.which(command[0])
        if executable:
            subprocess.Popen([executable, *command[1:]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return command[0]
    raise HTTPException(status_code=501, detail="This application is not installed or supported on this device.")


def _open_app(target: str) -> dict:
    system = platform.system()
    if target == "browser":
        webbrowser.open("https://www.google.com")
        return {"ok": True, "message": "Opened the default browser."}

    if system == "Linux":
        choices = {
            "calculator": [["gnome-calculator"], ["kcalc"], ["galculator"]],
            "files": [["xdg-open", os.path.expanduser("~")]],
            "terminal": [["x-terminal-emulator"], ["gnome-terminal"], ["konsole"]],
            "code": [["code"]],
        }
    elif system == "Windows":
        choices = {
            "calculator": [["calc.exe"]],
            "files": [["explorer.exe"]],
            "terminal": [["wt.exe"], ["cmd.exe"]],
            "code": [["code"]],
        }
    elif system == "Darwin":
        choices = {
            "calculator": [["open", "-a", "Calculator"]],
            "files": [["open", "-a", "Finder"]],
            "terminal": [["open", "-a", "Terminal"]],
            "code": [["code"]],
        }
    else:
        raise HTTPException(status_code=501, detail="This operating system is not supported.")

    if target not in choices:
        raise HTTPException(status_code=400, detail="That application is not in the approved list.")
    launched = _start_first_available(choices[target])
    return {"ok": True, "message": f"Started {target}.", "command": launched}


def _open_website(target: str) -> dict:
    websites = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "github": "https://github.com",
    }
    url = websites.get(target)
    if not url:
        raise HTTPException(status_code=400, detail="That website is not in the approved list.")
    webbrowser.open(url)
    return {"ok": True, "message": f"Opened {target.title()}."}


def _volume(target: str) -> dict:
    if platform.system() != "Linux":
        raise HTTPException(
            status_code=501,
            detail="Volume automation is currently implemented for Linux with PipeWire or PulseAudio.",
        )
    wpctl = shutil.which("wpctl")
    pactl = shutil.which("pactl")
    if wpctl:
        commands = {
            "mute": [wpctl, "set-mute", "@DEFAULT_AUDIO_SINK@", "1"],
            "unmute": [wpctl, "set-mute", "@DEFAULT_AUDIO_SINK@", "0"],
            "up": [wpctl, "set-volume", "@DEFAULT_AUDIO_SINK@", "5%+"],
            "down": [wpctl, "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-"],
        }
    elif pactl:
        commands = {
            "mute": [pactl, "set-sink-mute", "@DEFAULT_SINK@", "1"],
            "unmute": [pactl, "set-sink-mute", "@DEFAULT_SINK@", "0"],
            "up": [pactl, "set-sink-volume", "@DEFAULT_SINK@", "+5%"],
            "down": [pactl, "set-sink-volume", "@DEFAULT_SINK@", "-5%"],
        }
    else:
        raise HTTPException(status_code=501, detail="Install PipeWire (wpctl) or PulseAudio (pactl).")
    if target not in commands:
        raise HTTPException(status_code=400, detail="Unsupported volume action.")
    result = subprocess.run(commands[target], capture_output=True, text=True, timeout=5, check=False)
    if result.returncode:
        raise HTTPException(status_code=500, detail="The operating system rejected the volume command.")
    return {"ok": True, "message": f"Volume {target} completed."}


def _system_status() -> dict:
    try:
        import psutil
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="Install KAREN OS with the [agent] extra for system metrics.") from exc
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(os.path.expanduser("~"))
    battery = psutil.sensors_battery()
    return {
        "ok": True,
        "platform": platform.platform(),
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "memory_percent": memory.percent,
        "memory_available_gb": round(memory.available / (1024 ** 3), 2),
        "disk_percent": disk.percent,
        "battery_percent": battery.percent if battery else None,
        "battery_plugged": battery.power_plugged if battery else None,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "karenos-local-agent", "bind": "127.0.0.1"}


@app.get("/api/status")
async def status(x_karen_agent_token: str | None = Header(default=None)) -> dict:
    _check_token(x_karen_agent_token)
    return _system_status()


@app.post("/api/actions")
async def run_action(
    payload: ActionRequest,
    x_karen_agent_token: str | None = Header(default=None),
) -> dict:
    _check_token(x_karen_agent_token)
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="The action must be explicitly confirmed.")
    if payload.action == "open_app":
        return _open_app(payload.target)
    if payload.action == "open_website":
        return _open_website(payload.target)
    if payload.action == "volume":
        return _volume(payload.target)
    if payload.action == "system_status":
        return _system_status()
    raise HTTPException(status_code=400, detail="Unsupported action.")
