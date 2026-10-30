# KAREN OS

**A modular, browser-accessible personal AI assistant built with Python.**

KAREN OS is a learning and portfolio project inspired by fictional personal AI assistants. It combines a terminal chat interface, local conversation history, an optional hosted AI provider, optional speech output, and an explicitly launched webcam preview.

> **Status: v0.3.0 browser MVP.** KAREN OS is a user-space assistant application, not a replacement operating system or a fully autonomous AI. It now includes a browser chat interface and a server-side AI integration. Voice input, wake-word activation, direct device camera access, hardware integration, and a desktop HUD remain future work.

## Features in v0.3.0

- **Browser assistant:** responsive chat page for phones, tablets, and computers.
- **Voice controls:** optional browser speech recognition and spoken responses.
- **Web backend:** input limits, basic rate limit, server-side API key, and optional app password for public hosting.
- **Offline demo mode:** launch and test the program without an API key.
- **AI integration:** server-side integration with OpenAI-compatible providers (OpenAI, Gemini, Groq, and OpenRouter).
- **Local memory:** conversation history stored in a JSON file on your computer.
- **Optional speech output:** text-to-speech using `pyttsx3`.
- **Optional vision preview:** manually launched webcam preview using OpenCV.
- **Modular core:** asynchronous event bus and service lifecycle manager.
- **Automated tests:** pytest suite and GitHub Actions workflow.

## Quick start on Ubuntu / Linux

```bash
git clone https://github.com/jimberith/KAREN-OS.git
cd KAREN-OS
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
karenos
```

The app starts in offline demo mode with no API key. You can also run it as a Python module:

```bash
python -m karenos
```

## Run from any device with GitHub Codespaces

You can run the terminal version in a cloud development environment:

1. Open the repository and choose **Code → Codespaces → Create codespace on main**.
2. Wait for the Codespace to prepare the environment.
3. In its terminal, run `karenos`.

To enable AI responses, add your API credentials as GitHub Codespaces secrets. See [docs/CODESPACES.md](docs/CODESPACES.md) for the full instructions and security notes.

Codespaces runs the terminal app remotely. For a public browser URL, deploy the web application using the Render instructions below.

## Deploy the browser app to a public URL

A Render Blueprint is included in the repository. Follow [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) to deploy the web interface and configure private server environment variables. Do not commit API keys or paste them into source files.

## Enable AI responses

Install the optional AI dependency:

```bash
python -m pip install -e ".[ai]"
```

Edit the local `.env` file:

```env
KAREN_AI_API_KEY=your_provider_api_key
KAREN_AI_BASE_URL=https://api.openai.com/v1
KAREN_AI_MODEL=your-provider-supported-model
```

Use a model identifier available to your provider account. The project does not include an API key. Keep `.env` private and never commit it.

## Optional features

**Speech output**

```bash
python -m pip install -e ".[voice]"
```

Set `KAREN_TTS_ENABLED=true` in `.env`. Some Linux installations also need a system speech engine such as eSpeak.

**Camera preview**

```bash
python -m pip install -e ".[vision]"
karenos-camera
```

Press Q in the preview window to close it. KAREN OS does not activate the webcam in the background.

## Run the tests

```bash
python -m pip install -e ".[dev]"
pytest
ruff check src tests
```

## Where is conversation memory saved?

By default:

```text
~/.local/share/karenos/conversations.json
```

Set `KAREN_DATA_DIR` in `.env` to use another directory. Use `/clear` inside the app to delete the saved conversation history.

## Repository structure

```text
src/karenos/
  brain/       Assistant and AI provider adapter
  core/        Event bus and service lifecycle
  memory/      Local JSON conversation store
  ui/          Terminal interface
  vision/      Optional webcam preview
  voice/       Optional text-to-speech
tests/         Unit tests
docs/          Architecture, installation, and roadmap
```

## Privacy and safety

- The base app stores conversation history locally in plain JSON. Anyone with access to your user account can read that file.
- When an AI provider is configured, prompts and the selected recent chat history are sent to that provider.
- Camera access happens only after manually launching `karenos-camera`.
- This release does not perform face recognition, continuous microphone recording, desktop control, or hardware actuation.
- Do not commit API keys, private conversations, webcam recordings, or downloaded model weights.

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for planned voice input, wake-word activation, object detection, a desktop dashboard, richer memory, and hardware integrations. Roadmap items are not current features.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

MIT. See [LICENSE](LICENSE).

## Run KAREN OS in a browser (hosted web app)

The repository includes a responsive browser interface and a Python API server. To run it locally:

```bash
python -m pip install -e ".[web]"
cp .env.example .env
```

Set `KAREN_AI_API_KEY` and `KAREN_AI_MODEL` in your local, untracked `.env` file, then run:

```bash
uvicorn karenos.web.app:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser.

### Deploy to a public URL with Render

A `render.yaml` Blueprint is included:

1. Create or sign in to a Render account.
2. Choose **New → Blueprint**.
3. Connect your GitHub account and select `jimberith/KAREN-OS`.
4. Render reads `render.yaml` and asks for the three private values.
5. Enter a **newly rotated** OpenAI API key, a model available to your API account, and a unique KAREN app access password.
6. Create the Blueprint and wait for the first deploy to finish.
7. Open the Render-provided HTTPS URL on your phone, laptop, or tablet.

The API key is held by the server as an environment variable. It is not embedded in browser JavaScript or committed to Git. The access password prevents visitors from using the app without authorization.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the complete guide and security notes.
