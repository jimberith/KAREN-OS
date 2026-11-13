# KAREN OS

**A modular, browser-accessible personal AI assistant built with Python.**

KAREN OS is a user-space personal assistant project. It is inspired by fictional AI assistants, but it is not a replacement operating system or a fully autonomous system. Its browser application runs in GitHub Codespaces or on a Python host, while a separate local companion can perform a small set of approved actions on your physical computer.

## v0.4.1 — multimodal command console

KAREN routes natural-language requests to the appropriate feature:

- **AI conversation:** Gemini native API or an OpenAI-compatible provider.
- **Intent routing:** detects common commands before calling the model.
- **Web search:** retrieves public search results and shows source links.
- **Persistent memory:** SQLite conversation history and private notes, scoped to a browser session.
- **Visual understanding:** user-uploaded images or one camera snapshot analysed by Gemini.
- **Image generation:** Gemini 3.1 Flash Image; generated files are stored in the KAREN data directory.
- **Voice input/output:** browser speech recognition and browser speech synthesis.
- **Device automation:** optional local companion for an allowlist of website/app/volume/status actions. Every action requires an explicit confirmation.
- **System dashboard:** CPU, RAM, disk and battery metrics when the local companion is connected.

The camera is not continuously recording. Voice recognition availability depends on the browser. Device controls work only when the local companion is installed and running on the physical computer. The model cannot run arbitrary shell commands.

See [docs/FEATURES.md](docs/FEATURES.md) for supported commands and limitations.

## Quick start: GitHub Codespaces

1. Open [KAREN-OS](https://github.com/jimberith/KAREN-OS).
2. Select **Code → Codespaces → Create codespace on main**.
3. Wait for the environment setup.
4. Open **Terminal → New Terminal**.
5. Run:

```bash
git pull --ff-only origin main
python -m pip install -e ".[web,agent]"
karenos-web
```

Keep that terminal running. In the **Ports** tab, open port **8000** in the browser. Keep port 8000 **Private**.

If an older KAREN server is already running, press **Ctrl+C** in its terminal once before running `karenos-web`. The launcher checks for a healthy existing server and avoids starting a duplicate.

## Configure AI

In GitHub **Settings → Codespaces → Codespaces secrets**, add these repository-restricted secrets:

| Secret | Value |
|---|---|
| `KAREN_AI_API_KEY` | API key from your selected provider |
| `KAREN_AI_BASE_URL` | Provider base URL |
| `KAREN_AI_MODEL` | Model ID from that provider |

For Gemini, use a key from [Google AI Studio](https://aistudio.google.com/apikey), base URL `https://generativelanguage.googleapis.com/v1beta/openai/`, and a model ID currently enabled for your project. Gemini's native API is used for vision and image generation. Never commit API keys or paste them into public code, issues or screenshots.

After changing Codespaces secrets, stop and restart the Codespace so the environment receives them.

## Connect your physical computer

Codespaces runs remotely. It cannot directly launch applications on your laptop or adjust your laptop's volume. To enable those functions, install the local companion on the physical computer:

```bash
git clone https://github.com/jimberith/KAREN-OS.git
cd KAREN-OS
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[agent]"
karenos-agent
```

The agent binds only to `127.0.0.1:8765`, generates a private token on first launch, and prints it once. In KAREN OS open **Settings**, use `http://127.0.0.1:8765`, paste the token, and select **Save & Connect**. If the browser asks permission for local-network access, allow it for your KAREN Codespaces page.

The local companion is currently tested as a Linux-focused first implementation. App availability depends on installed desktop software. Volume control needs PipeWire (`wpctl`) or PulseAudio (`pactl`). Do not expose port 8765 to your LAN or the public internet.

## Local run (Ubuntu/Linux)

```bash
git clone https://github.com/jimberith/KAREN-OS.git
cd KAREN-OS
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[web,agent]"
cp .env.example .env
karenos-web
```

Edit `.env` locally to configure the provider. Keep it private; `.env` is excluded by `.gitignore`.

## Main natural-language commands

- `Search the web for the latest ...`
- `Remember that ...`
- `What do you remember?`
- `Generate an image of ...`
- `Open YouTube`, `Open Google`, `Open GitHub`
- `Launch calculator`, `Open files`, `Open terminal`, `Open VS Code`
- `Mute volume`, `Unmute`, `Volume up`, `Volume down`
- `Show system status`

For device actions, KAREN presents a confirmation card. Only the approved local agent action is sent after you confirm it.

## Development and verification

Install dev dependencies and run tests:

```bash
python -m pip install -e ".[dev,web,agent]"
pytest
ruff check src tests
```

GitHub Actions runs the test suite on Python 3.10, 3.11 and 3.12.

## Security and known limitations

- AI API keys remain on the server, never in browser JavaScript.
- Codespaces port 8000 should remain Private.
- Public deployments must set `KAREN_REQUIRE_ACCESS_CODE=true` and a strong `KAREN_ACCESS_PASSWORD`.
- Local agent actions are allowlisted, token-protected, and confirmation-gated.
- Browser camera analysis is snapshot-based and requires permission.
- Browser speech recognition may use the browser's speech service and is not available in every browser.
- SQLite memory and generated images are stored in the KAREN data directory; back up or delete that directory to manage local data.
- Image generation, AI requests and web search are subject to provider availability, quotas, and billing.
- KAREN does not yet provide a continuous wake word, full-duplex low-latency voice conversation, multi-frame video understanding, a persistent desktop HUD, calendar actions or arbitrary file management. Those are future roadmap items.

## Documentation

- [Features and supported commands](docs/FEATURES.md)
- [Codespaces setup](docs/CODESPACES.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
