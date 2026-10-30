# Running KAREN OS with GitHub Codespaces

GitHub Codespaces runs this repository in a cloud development environment. You can open that environment in a browser on another computer without installing Python on that computer.

## 1. Create a Codespace

1. Open https://github.com/jimberith/KAREN-OS
2. Select the green **Code** button.
3. Open the **Codespaces** tab.
4. Select **Create codespace on main**.
5. Wait for the cloud environment to finish setting up.

This repository includes a Dev Container configuration. It installs the project's base development dependencies automatically after the Codespace is created.

## 2. Start KAREN OS

Open the integrated terminal in Codespaces and run:

```bash
karenos
```

The current application is a terminal assistant. It starts in offline demo mode when no AI provider key is configured.

Useful commands inside the assistant:

- `/help` displays available commands.
- `/clear` deletes saved local conversation history.
- `/quit` exits the application.

## 3. Enable AI integration securely

Do not place an API key in a committed file, README, source code, or chat message.

1. Open your GitHub profile menu and select **Settings**.
2. Open **Codespaces** under **Code, planning, and automation**.
3. Find **Codespaces secrets**, then select **New secret**.
4. Create a secret named `KAREN_AI_API_KEY` and paste your provider API key as its value.
5. Give the secret access to the `KAREN-OS` repository and save it.
6. If needed, create these additional Codespaces secrets:
   - `KAREN_AI_BASE_URL` with value `https://api.openai.com/v1`
   - `KAREN_AI_MODEL` with a model identifier supported by your API account
7. Stop and recreate/restart the Codespace so the updated secret is available in its environment, then run `karenos` again.

Codespaces secrets are exposed to the running development environment as environment variables. The application loads these variables directly. The AI provider key is not stored in the Git repository.

## 4. Use the same project from another device

Sign in to GitHub from the other device, open this repository, and open the existing Codespace from the **Code → Codespaces** menu. You can also create a new Codespace if you need a separate environment.

Your Codespace is a cloud development machine, not a permanently running public assistant server. It may stop when idle, and usage is subject to GitHub Codespaces quotas and billing settings.

## 5. Understand the current limitation

KAREN OS v0.1.0 is a command-line application. Codespaces lets you use its terminal remotely, but it does not turn the assistant into a mobile-friendly web app. A public URL with a chat screen requires a web interface and a hosted application service.

The webcam preview and local audio features are also not guaranteed to work through a cloud Codespace because the application runs on the remote machine, not directly on the device's local webcam or speakers.
