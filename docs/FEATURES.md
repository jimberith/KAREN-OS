# KAREN OS v0.4.0 — feature guide

## 1. One command interface

Type naturally in the main chat box. KAREN routes obvious commands locally; ambiguous questions go to the selected AI model.

| Example request | Module | Result |
|---|---|---|
| "Explain OFDM" | AI conversation | Model-generated answer |
| "Search the web for latest AI news" | Web search | Search links and answer context |
| "Remember that my project is KAREN OS" | Memory | Saves a private note |
| "What do you remember?" | Memory | Lists saved notes in this browser session |
| "Generate an image of a futuristic assistant" | Image generation | Creates an image in the KAREN workspace |
| "Open YouTube" | Device automation | Confirmation card; opens only after confirmation and local-agent connection |
| "Launch calculator" | Device automation | Confirmation card; requires local agent |
| "Mute volume" | Device automation | Confirmation card; Linux PipeWire/PulseAudio support |
| "Show system status" | Device dashboard | Local CPU/RAM/disk/battery status, if connected |

Anything not matched by a deterministic intent rule is handled as ordinary AI chat. The intent router does not run user-supplied shell commands.

## 2. Conversation, history and memory

- Chat exchanges are written to SQLite in the configured KAREN data directory.
- Browser sessions have separate IDs.
- "Remember that ..." creates a note associated with the browser session.
- "What do you remember?" retrieves the latest notes.
- The Memory panel can add, delete, and export notes.
- Clear Conversation removes messages but does not delete saved notes.

Memory is not encrypted at rest by this version. Protect the host account and its data directory. Do not save passwords, API keys, or sensitive personal information as notes.

## 3. Web search

KAREN uses the DDGS search library and shows clickable result links. Search results are external, untrusted content. Verify important information from the source pages. Search can fail due to network conditions, upstream changes or provider limits.

## 4. Visual understanding

- Upload JPG, PNG or WEBP up to 8 MB with the IMAGE control.
- Or use CAMERA to request browser permission and capture one still frame.
- The captured frame is sent to Gemini for description.
- The user chooses when the camera starts and which frame is sent. There is no background recording.

This is image understanding, not a continuously running object-tracking pipeline or a promise of identifying people.

## 5. Image generation

KAREN sends the prompt to Gemini 3.1 Flash Image. Generated image data is saved under `data/generated` (or the configured `KAREN_DATA_DIR`) and served through the application. Image generation requires model access and may incur provider charges.

## 6. Voice

- VOICE uses the browser's SpeechRecognition/Web Speech API where available.
- KAREN VOICE prefers the Gemini 3.8 Flash-Lite TTS service (`gemini-3.8-flash-lite-tts`, voice `Kore`) when Gemini is configured.
- If the server TTS service is unavailable or another provider is selected, KAREN VOICE falls back to the browser's speechSynthesis API.
- The optional TTS settings are `KAREN_TTS_MODEL` and `KAREN_TTS_VOICE`.
- TTS output is generated on demand, only while the user has enabled spoken replies. This is not continuous listening.
- Browser speech recognition support and language availability vary. This version is not a custom wake-word detector or a streaming full-duplex voice interface.

Google's current TTS model documentation: https://ai.google.dev/gemini-api/docs/speech-generation

## 7. Local device companion

Install the `agent` extra and run `karenos-agent` on the physical computer. The service binds only to loopback at `127.0.0.1:8765`, requires a random local token, and exposes only approved targets:

- Websites: YouTube, Google and GitHub.
- Applications: calculator, file manager, terminal, VS Code and default browser, depending on OS and installed applications.
- Linux volume: mute/unmute/up/down through `wpctl` or `pactl`.
- System information: CPU, RAM, disk and battery where supported by psutil.

Every action requires a confirmation click in KAREN. The agent rejects unconfirmed actions and does not have an arbitrary command-execution API.

For a Codespaces browser to reach localhost, the browser may prompt for local-network access. Grant it only to your own KAREN session. Some browser versions or policies may block this; in that case, use KAREN's cloud-side features and run the agent from a local browser/app environment.

## 8. Security boundaries

- Do not commit API keys.
- Keep Codespaces port 8000 Private.
- For a public hosting provider, set `KAREN_REQUIRE_ACCESS_CODE=true` and configure `KAREN_ACCESS_PASSWORD`.
- Never expose local-agent port 8765 to a network.
- A confirmation card is not a substitute for reviewing the action.
- Do not store secrets in memory notes.

## 9. Not implemented yet

Wake word, continuous video understanding, real-time bidirectional audio, custom voice cloning, multi-agent planning, calendar/email integration, long-term vector search, file-system operations, and an always-on desktop HUD are roadmap items, not v0.4 features.
