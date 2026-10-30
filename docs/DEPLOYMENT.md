# Browser deployment guide

KAREN OS v0.3 adds a responsive browser interface served by a FastAPI backend. The browser never receives the OpenAI API key. The backend reads it from a private environment variable and sends requests to the OpenAI API.

## Deploy on Render

The repository root contains `render.yaml`, which defines a Render web service.

1. Create or sign in to a Render account.
2. In the Render Dashboard, choose **New → Blueprint**.
3. Connect your GitHub account if asked.
4. Select the `jimberith/KAREN-OS` repository and the `main` branch.
5. Render reads `render.yaml`. During the initial Blueprint creation, provide:
   - `KAREN_AI_API_KEY`: a new key created after revoking the exposed key.
   - `KAREN_AI_MODEL`: a model identifier enabled for your API account.
   - `KAREN_ACCESS_PASSWORD`: a long, unique password that people must enter before using your KAREN OS website. Render enables this check with `KAREN_REQUIRE_ACCESS_CODE=true`.
6. Finish creating the Blueprint and wait for the deployment to succeed.
7. Open the HTTPS URL Render assigns to the service. The same URL works from supported browsers on phones, tablets, and computers.

Do not put API keys in the Git repository, frontend JavaScript, screenshots, issues, or chat messages. Render stores environment variables separately from the source repository and injects them into the running service. See the [Render environment variable guide](https://render.com/docs/configure-environment-variables) and [Blueprint reference](https://render.com/docs/blueprint-spec).

## Run locally

From the repository root, create and activate a Python virtual environment, then install the web extra:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[web]"
cp .env.example .env
```

Edit `.env` locally and set:

```env
KAREN_AI_API_KEY=<YOUR_NEW_API_KEY>
KAREN_AI_MODEL=<MODEL_AVAILABLE_TO_YOUR_API_ACCOUNT>
KAREN_ACCESS_PASSWORD=<YOUR_PRIVATE_APP_PASSWORD>
```

Then run:

```bash
uvicorn karenos.web.app:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`.

## Security controls in this version

- The OpenAI key is read only by the backend from `KAREN_AI_API_KEY`.
- The browser sends a separate app access code in a request header. The code is held in the current browser tab's session storage, not committed to source.
- The backend compares access codes using a constant-time comparison.
- Chat input has message-count and text-length limits.
- The API applies a basic per-client request limit.
- Basic browser security headers are enabled.
- Conversation context is kept in the current page session. It is not saved to a server database; refreshing the page clears the chat.
- The browser version supports optional speech input and speech output using browser speech APIs. Recognition support and audio handling depend on the browser. Camera analysis is not implemented yet.

## Hosting and usage notes

Render's free web services may spin down when idle and can take time to start again. Free plans also have resource and usage limits. Check Render's current plan and billing details before relying on this as an always-on service. OpenAI API usage is billed separately according to your API account and model.

## Codespaces without a second app login

In GitHub Codespaces, `KAREN_REQUIRE_ACCESS_CODE` is false by default. Keep port 8000 Private; GitHub controls access to the forwarded port. Do not make an unauthenticated Render deployment public.

## Troubleshooting

- **The page says setup required:** add `KAREN_ACCESS_PASSWORD` in Render's Environment settings and redeploy.
- **The page says AI setup required:** add `KAREN_AI_API_KEY` and `KAREN_AI_MODEL` as environment variables.
- **Access code rejected:** enter the exact `KAREN_ACCESS_PASSWORD` value saved on Render.
- **AI provider request failed:** inspect the Render service logs. Confirm the key is active, billing is configured on the OpenAI API account, and the model identifier is available to that account.
- **Page is unavailable:** check the latest Render deployment and the `/health` health-check endpoint.
