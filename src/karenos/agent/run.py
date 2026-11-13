"""Start the loopback-only local agent and provision a private access token."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

import uvicorn


def _token_path() -> Path:
    config_home = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")).expanduser()
    folder = config_home / "karenos"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "agent_token"


def main() -> None:
    token_path = _token_path()
    token = os.getenv("KAREN_LOCAL_AGENT_TOKEN", "").strip()
    if not token:
        if token_path.exists():
            token = token_path.read_text(encoding="utf-8").strip()
        else:
            token = secrets.token_urlsafe(32)
            token_path.write_text(token, encoding="utf-8")
            try:
                token_path.chmod(0o600)
            except OSError:
                pass
            print("\nKAREN OS local-agent token (enter it in KAREN Settings once):")
            print(token)
            print(f"Saved privately to: {token_path}\n")
        os.environ["KAREN_LOCAL_AGENT_TOKEN"] = token

    print("KAREN OS local agent listening only on http://127.0.0.1:8765")
    print("Do not expose this port to your network. Close this terminal to stop the agent.")
    uvicorn.run("karenos.agent.app:app", host="127.0.0.1", port=8765, log_level="info")


if __name__ == "__main__":
    main()
