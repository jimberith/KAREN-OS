# KAREN OS

**A modular, laptop-first personal AI assistant built with Python.**

KAREN OS is a learning and portfolio project inspired by fictional personal AI assistants. It combines a terminal chat interface, local conversation history, an optional hosted AI provider, optional speech output, and an explicitly launched webcam preview.

> **Status: v0.1.0 foundation.** This is a user-space assistant application, not a replacement operating system or an autonomous AI. The current version is designed to run on a Linux laptop first. Hardware integration, wake-word activation, and a desktop HUD are future work.

## Features in v0.1.0

- **Terminal assistant:** simple interactive chat with `/help`, `/clear`, and `/quit`.
- **Offline demo mode:** launch and test the program without an API key.
- **Optional AI provider:** adapter for services that support the OpenAI Chat Completions API.
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

Codespaces runs the terminal app remotely. It does not yet provide a public mobile chat website or direct access to the device's local webcam and microphone.

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

Set `KAREN_AI_API_KEY`, `KAREN_AI_MODEL`, and `KAREN_ACCESS_PASSWORD` in your local, untracked `.env` file, then run:

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
