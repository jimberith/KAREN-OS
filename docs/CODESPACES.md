# Running KAREN OS in GitHub Codespaces

GitHub Codespaces gives you a cloud development machine. You can run KAREN OS there and open its forwarded browser interface.

## 1. Create or open a Codespace

1. Open https://github.com/jimberith/KAREN-OS.
2. Select **Code → Codespaces**.
3. Create or open a Codespace on `main`.
4. Wait for the Dev Container setup to finish. It installs the project dependencies and forwards port 8000 privately.

## 2. Add the two required Codespaces secrets

The API key previously pasted into chat must remain revoked. Use your replacement key.

In GitHub **Settings → Codespaces → Codespaces secrets**, create these secrets and grant access only to `KAREN-OS`:

| Secret name | Value |
|---|---|
| `KAREN_AI_API_KEY` | Your replacement OpenAI API key |
| `KAREN_AI_MODEL` | `gpt-5.6-luna` if enabled for your API project |

The documented model ID is listed in the [OpenAI API model catalogue](https://platform.openai.com/docs/models). If your project does not have access, choose a model shown as available in your own API account.

An app-level password is no longer required for a private Codespaces port. The forwarded port must remain **Private**; GitHub account access controls who can open it. Do not change the port visibility to Public.

If you previously created `KAREN_ACCESS_PASSWORD`, it is ignored in Codespaces mode unless `KAREN_REQUIRE_ACCESS_CODE=true`. You may delete that old Codespaces secret if you no longer need it.

After changing secrets, stop and restart the Codespace so the environment receives the updates.

## 3. Start the browser application

Open **Terminal → New Terminal**, then run:

```bash
git pull --ff-only origin main
python -m pip install -e ".[web]"
uvicorn karenos.web.app:app --host 0.0.0.0 --port 8000
```

Keep the terminal running.

## 4. Open the private forwarded port

1. Open the **Ports** tab in the bottom panel.
2. Find port `8000`.
3. Confirm its visibility is **Private**.
4. Select **Open in Browser**.

The browser app opens without a separate KAREN password screen. GitHub's private forwarded port is the access boundary.

## 5. Use voice features

The browser interface includes:
- **VOICE**: uses your browser's speech recognition, if supported. The browser will ask for microphone permission.
- **SPEAK**: reads KAREN's responses using the browser's speech synthesis.

Voice recognition support depends on the browser and its speech service. Browser or operating-system speech services may process audio outside the KAREN backend. Use text chat if you do not want to grant microphone access.

## 6. If AI responses fail

The web app now shows a more specific message for common errors:
- API key rejected: check that the replacement key is active.
- Model not found: check `KAREN_AI_MODEL`; the current documented example is `gpt-5.6-luna`.
- Model permission denied: check model access for the API project.
- Credits or spend limit exhausted: check [OpenAI API billing](https://platform.openai.com/settings/organization/billing/overview).
- Network problem: check the Codespaces terminal output.

The API key stays in the Codespaces environment and is only used by the backend. Never put it in browser code, source files, or screenshots.

## 7. Use KAREN OS from another device

Sign in to the same GitHub account on the other device, open https://github.com/codespaces, resume this Codespace, start the server if needed, and open its private forwarded port. A Codespace is not an always-on production server and may stop when idle.

For public hosting, use the Render deployment guide. Public hosting requires a separate app access code to protect your API quota.
