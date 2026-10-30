# Installation on Ubuntu / Linux

## 1. Check Python

KAREN OS requires Python 3.10 or newer.

```bash
python3 --version
```

## 2. Clone the repository

```bash
git clone https://github.com/jimberith/KAREN-OS.git
cd KAREN-OS
```

## 3. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Activate the environment again whenever you open a new terminal for this project.

## 4. Install KAREN OS

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## 5. Configure

```bash
cp .env.example .env
```

Keep the API key blank to try offline demo mode. For hosted AI, add the provider API key and a model name supported by your provider to `.env`. Never commit that file.

## 6. Launch

```bash
karenos
```

You can also use:

```bash
python -m karenos
```

## Optional camera

```bash
python -m pip install -e ".[vision]"
karenos-camera
```

Press Q in the camera window to close it. The app does not open the camera unless this command is launched.

## Optional speech output

Install the optional dependency:

```bash
python -m pip install -e ".[voice]"
```

Set `KAREN_TTS_ENABLED=true` in `.env`, then launch `karenos`. Linux may also require a system speech engine such as eSpeak.

## Run tests

```bash
pytest
```
