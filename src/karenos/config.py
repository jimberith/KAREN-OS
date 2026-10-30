"""Runtime settings loaded from environment variables and an optional .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def default_data_dir() -> Path:
    override = os.getenv("KAREN_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".local" / "share" / "karenos"


@dataclass(frozen=True, slots=True)
class Settings:
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = ""
    data_dir: Path = default_data_dir()
    tts_enabled: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            ai_api_key=os.getenv("KAREN_AI_API_KEY", "").strip(),
            ai_base_url=os.getenv("KAREN_AI_BASE_URL", "https://api.openai.com/v1").strip(),
            ai_model=os.getenv("KAREN_AI_MODEL", "").strip(),
            data_dir=default_data_dir(),
            tts_enabled=os.getenv("KAREN_TTS_ENABLED", "false").lower() in {"1", "true", "yes"},
            log_level=os.getenv("KAREN_LOG_LEVEL", "INFO").strip(),
        )
