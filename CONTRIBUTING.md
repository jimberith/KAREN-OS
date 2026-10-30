# Contributing

Thank you for considering a contribution to KAREN OS.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Before submitting changes

- Add or update tests for changed behavior.
- Run `pytest`.
- Run `ruff check src tests`.
- Keep optional integrations optional.
- Never commit API keys, personal data, recordings, or downloaded model weights.
- Document permissions and safety implications for hardware or desktop-control features.

Keep pull requests focused and include steps to reproduce the change.
