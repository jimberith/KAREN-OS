# Roadmap

## v0.1.0–v0.3.4 — foundation and browser MVP

- [x] Modular Python package, CLI and service lifecycle
- [x] Browser chat and provider configuration
- [x] Gemini native API integration with timeout/overload fallback
- [x] Automated tests and GitHub Actions

## v0.4.0–v0.4.1 — multimodal command console

- [x] Natural-language intent routing for chat, search, memory, image generation and device actions
- [x] DuckDuckGo-powered web search with clickable result sources
- [x] Persistent SQLite chat history scoped by browser session
- [x] User-controlled memory notes with search, delete and JSON export
- [x] User-triggered image upload and camera snapshot analysis
- [x] Gemini 3.1 Flash Image generation and workspace storage
- [x] Browser speech recognition and browser speech synthesis fallback
- [x] Optional Gemini 3.8 Flash-Lite server-generated TTS
- [x] Local companion agent bound to 127.0.0.1
- [x] Allowlisted desktop actions with explicit confirmation
- [x] Local system telemetry dashboard
- [x] One-command web and local-agent launchers

## Planned v0.5 — deeper assistant intelligence

- [ ] Streaming spoken responses and lower-latency voice conversation
- [ ] Better entity-aware memory retrieval and user-editable preferences
- [ ] Background task queue with task history and cancellation
- [ ] More robust search providers and source quality checks
- [ ] Optional document ingestion and semantic retrieval

## Planned v0.6 — advanced perception and integrations

- [ ] Multi-frame video understanding with explicit capture controls
- [ ] Wake-word service running locally with visible microphone state
- [ ] Calendar, reminders and approved external integrations
- [ ] User-approved file search and file operations
- [ ] Local desktop overlay / HUD with permission controls

## Security principles

- API keys remain server-side.
- Local device actions are allowlisted and require user confirmation.
- The companion binds to loopback only, never to a LAN interface.
- Camera and microphone require explicit user action.
- User memory can be exported and deleted.
- No arbitrary shell command execution is exposed to the model or browser.
