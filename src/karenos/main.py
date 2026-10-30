"""KAREN OS command-line entry point."""

from __future__ import annotations

import logging

from karenos.brain.assistant import Assistant
from karenos.config import Settings
from karenos.memory.store import ConversationStore
from karenos.ui.dashboard import run_terminal
from karenos.voice.speech import SpeechOutput


def main() -> None:
    settings = Settings.from_env()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    memory = ConversationStore(settings.data_dir / "conversations.json")
    assistant = Assistant(settings=settings, memory=memory)
    speech = SpeechOutput() if settings.tts_enabled else None
    run_terminal(assistant=assistant, memory=memory, speech=speech)


if __name__ == "__main__":
    main()
