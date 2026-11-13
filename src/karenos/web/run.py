"""One-command launcher for the KAREN OS browser app."""

from __future__ import annotations

import os
import socket
import urllib.error
import urllib.request

import uvicorn


def main() -> None:
    host = "127.0.0.1"
    port = int(os.getenv("PORT", "8000"))
    try:
        with socket.create_connection((host, port), timeout=1.0):
            try:
                with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=2.0) as response:
                    if response.status == 200:
                        print(f"KAREN OS is already running on port {port}. Open the forwarded port.")
                        return
            except (urllib.error.URLError, TimeoutError):
                pass
            raise SystemExit(
                f"Port {port} is already occupied by another process. Stop that process before starting KAREN OS."
            )
    except OSError:
        pass

    print(f"Starting KAREN OS on 0.0.0.0:{port}. Keep this terminal open.")
    uvicorn.run("karenos.web.app:app", host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
