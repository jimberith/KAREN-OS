# Running KAREN OS in GitHub Codespaces

GitHub Codespaces gives you a cloud development machine. You can run KAREN OS there and open its forwarded browser interface.

## 1. Create or open a Codespace

1. Open https://github.com/jimberith/KAREN-OS.
2. Select **Code → Codespaces**.
3. Create or open a Codespace on `main`.
4. Wait for the Dev Container setup to finish. It installs the project dependencies and forwards port 8000 privately.

## 2. Choose an AI provider

KAREN OS supports OpenAI-compatible Chat Completions endpoints. You can use OpenAI, Google Gemini, Groq, or OpenRouter by changing the three Codespaces secrets below.

| Provider | API base URL | Example model ID |
|---|---|---|
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-3.8-flash` |
| Groq | `https://api.groq.com/openai/v1` | `openai/gpt-oss-120b` |
| OpenRouter | `https://openrouter.ai/api/v1` | `openrouter/free` |
| OpenAI | `https://api.openai.com/v1` | Use a model enabled for your API project |

Provider model IDs and free-tier access change. Verify the selected model in the provider's current dashboard before using it.

### Create a provider API key

- Google Gemini: https://aistudio.google.com/apikey
- Groq: https://console.groq.com/keys
- OpenRouter: https://openrouter.ai/keys
- OpenAI: https://platform.openai.com/api-keys

## 3. Configure GitHub Codespaces secrets

Open GitHub **Settings → Codespaces → Codespaces secrets**:

https://github.com/settings/codespaces

Create or edit these secrets. Give each access only to `KAREN-OS`.

| Secret name | What to enter |
|---|---|
| `KAREN_AI_API_KEY` | API key from the provider you selected |
| `KAREN_AI_BASE_URL` | Provider's API base URL from the table above |
| `KAREN_AI_MODEL` | Model ID from the provider's current catalogue |

The previous OpenAI key shared in chat should stay revoked. Never put a replacement key in a source file, browser JavaScript, screenshot, or chat message.

For Google Gemini's free tier, check its data-use terms before sending private or sensitive messages. Google's pricing page marks free-tier data as usable to improve its products. See https://ai.google.dev/gemini-api/docs/pricing.

OpenRouter offers free model variants, but free usage is rate-limited. Its current free plan lists a daily request cap; check the live limits at https://openrouter.ai/collections/free-models.

Groq's exact request/token limits depend on the model and account; see https://console.groq.com/docs/rate-limits.

After changing secrets, stop and restart the Codespace so the environment receives the updates.

### Important: match the API key to the provider

For Gemini, all three settings must be Gemini values:

- `KAREN_AI_API_KEY`: a Gemini API key copied from Google AI Studio.
- `KAREN_AI_BASE_URL`: `https://generativelanguage.googleapis.com/v1beta/openai/`.
- `KAREN_AI_MODEL`: `gemini-3.8-flash`.

An OpenAI key will not authenticate against the Gemini endpoint. A Gemini key will not authenticate against the OpenAI endpoint. Create/copy the Gemini key from https://aistudio.google.com/apikey, replace the existing `KAREN_AI_API_KEY` secret with it, and restart Codespaces. Newly created AI Studio keys are Auth keys; follow Google's key migration instructions if using an older key: https://ai.google.dev/gemini-api/docs/api-key.

To check the non-secret provider settings currently loaded by your Codespace, open the KAREN OS website and visit `/api/status` at the end of its URL. It shows only the provider hostname, model name, and whether a key is configured. It never displays the key itself.

## 4. Start the browser application

Open **Terminal → New Terminal**, then run:

```bash
git pull --ff-only origin main
python -m pip install -e ".[web]"
uvicorn karenos.web.app:app --host 0.0.0.0 --port 8000
```

Keep the terminal running.

## 5. Open the private forwarded port

1. Open the **Ports** tab in the bottom panel.
2. Find port `8000`.
3. Confirm its visibility is **Private**.
4. Select **Open in Browser**.

Codespaces mode does not show a second KAREN password screen. GitHub's private forwarded port controls access.

## 6. Browser voice controls

- **VOICE**: uses browser speech recognition when supported. Your browser asks for microphone permission.
- **SPEAK**: reads assistant replies aloud using browser speech synthesis.

Recognition and audio handling depend on the browser and its speech service. Use text chat if you do not want to grant microphone permission.

## 7. Use KAREN OS from another device

Sign in to the same GitHub account on another device, open https://github.com/codespaces, resume this Codespace, start the server if needed, and open its private forwarded port.

A Codespace is for development and testing. It can stop when idle. For public hosting, use the Render deployment guide and keep the app access code enabled.

## Notes

- The API key remains on the backend and is never sent to browser JavaScript.
- The browser sends conversation messages to the configured AI provider when you submit them.
- Chat history is held in the current browser page session; refreshing the page clears it.


## Gemini native API mode

For Google Gemini, the current KAREN backend uses the native `generateContent` REST endpoint with the `x-goog-api-key` header. This avoids reliance on the OpenAI compatibility authentication path.

Configure:

- `KAREN_AI_API_KEY`: Gemini API key from Google AI Studio.
- `KAREN_AI_BASE_URL`: `https://generativelanguage.googleapis.com/v1beta/openai/` (used to select Gemini provider mode).
- `KAREN_AI_MODEL`: `gemini-3.8-flash`.

The server sends the actual request to `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`.

If the key is rejected with HTTP 401, ensure `KAREN_AI_API_KEY` contains the full Gemini key, not an OpenAI key. Re-copy it from https://aistudio.google.com/apikey and update the Codespaces secret. Never paste the key into a chat or source file.
