# Running KAREN OS in GitHub Codespaces

GitHub Codespaces gives you a cloud development machine. You can run the KAREN OS browser application there and open its forwarded URL from a browser.

## 1. Create a Codespace

1. Open https://github.com/jimberith/KAREN-OS.
2. Select the green **Code** button.
3. Open the **Codespaces** tab.
4. Select **Create codespace on main**.
5. Wait for the Codespace to finish creating the Python environment.

The repository's `.devcontainer/devcontainer.json` installs the development and AI dependencies and configures port 8000 for automatic forwarding.

## 2. Add private Codespaces secrets

The old API key that was pasted into a chat must be revoked. Generate a replacement key first. Never paste the replacement into GitHub source files or into chat.

1. Open your GitHub profile menu, then **Settings**.
2. Under **Code, planning, and automation**, open **Codespaces**.
3. Find **Codespaces secrets** and select **New secret**.
4. Add the following secrets. Give them access only to the `KAREN-OS` repository.

| Secret name | Value |
|---|---|
| `KAREN_AI_API_KEY` | Your newly generated API key |
| `KAREN_AI_MODEL` | A model identifier enabled for your API account |
| `KAREN_ACCESS_PASSWORD` | A strong, unique password you choose for KAREN OS |

The app password is separate from your API key. Do not reuse your API key as the app password.

5. Save the secrets.
6. Stop and restart your Codespace so the new secrets are injected into its environment.

GitHub explains the Codespaces secret setup here: https://docs.github.com/en/codespaces/managing-your-codespaces/managing-your-account-specific-secrets-for-github-codespaces

## 3. Start the browser application

Open the integrated terminal in Codespaces and run:

```bash
uvicorn karenos.web.app:app --host 0.0.0.0 --port 8000
```

The server should start and show that it is listening on port 8000.

## 4. Open KAREN OS in your browser

1. In the bottom panel of the Codespaces editor, select the **Ports** tab.
2. Find port **8000**. The repository configuration asks Codespaces to forward it automatically.
3. Select the globe/open-in-browser icon or right-click the port and choose **Open in Browser**.
4. KAREN OS will open at a forwarded `https://...app.github.dev` URL.
5. Enter the private `KAREN_ACCESS_PASSWORD` you created as a Codespaces secret.

Keep the port visibility set to **Private** for personal use. A public forwarded port is accessible to anyone who knows its URL; the app's password is an additional safeguard, not a reason to publish secrets.

GitHub's port-forwarding guide: https://docs.github.com/en/codespaces/developing-in-a-codespace/forwarding-ports-in-your-codespace

## 5. Use KAREN OS from another device

Sign in to GitHub on the other device and reopen the same Codespace from https://github.com/codespaces. Start the server again if it is not already running, then open port 8000 from the Ports tab.

A Codespaces forwarded URL is useful for development and testing. The Codespace and its server can stop when idle or when the Codespace is stopped. For a persistent public website, deploy the app using the Render instructions in [DEPLOYMENT.md](DEPLOYMENT.md).

## Terminal-only version

You can also run the simpler command-line assistant in the Codespace:

```bash
karenos
```

Type `/help` for its commands and `/quit` to exit.

## Notes

- The OpenAI API key stays in the Codespace environment and is used by the Python backend. It is never included in browser JavaScript.
- Chat text is sent to your configured AI provider when you submit it.
- The browser chat history is held in the current page session; refreshing the page clears it.
- Browser camera and microphone access are not implemented in the web version yet.
- ChatGPT subscription billing and OpenAI API billing are separate.
