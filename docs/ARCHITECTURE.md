# Architecture

KAREN OS is a Python user-space application. It is not a replacement for Linux, Windows, or another operating system.

## Current runtime flow

1. The terminal interface receives a text prompt.
2. The assistant loads the last 20 conversation messages from the local JSON store.
3. When an AI provider is configured, the provider adapter sends the conversation to the configured Chat Completions endpoint. Without a provider, the app replies in offline demo mode.
4. The user prompt and assistant response are saved locally.

## Main modules

- `core/events.py`: asynchronous in-process publish/subscribe event bus.
- `core/service_manager.py`: explicit startup and reverse-order shutdown for optional services.
- `brain/assistant.py`: assistant orchestration and AI provider adapter.
- `memory/store.py`: local JSON conversation persistence.
- `voice/speech.py`: optional text-to-speech adapter.
- `vision/camera.py`: manually launched webcam preview.

Optional dependencies are imported only when their feature is used. This keeps the base installation small.

## Safety and privacy boundaries

The camera is opened only after the user explicitly launches `karenos-camera`. There is no continuous microphone recording, wake-word listener, face identification, desktop automation, or hardware control in this release. Future device-control features must use permission prompts, explicit allowlists, and an auditable action log.
