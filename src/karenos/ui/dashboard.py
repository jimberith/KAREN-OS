"""Interactive terminal interface for KAREN OS."""

from __future__ import annotations

from karenos.brain.assistant import Assistant
from karenos.memory.store import ConversationStore
from karenos.voice.speech import SpeechOutput


BANNER = r"""
 _  __   ___  ____  _____ _   _  ___  ____
| |/ /  / _ \|  _ \| ____| \ | |/ _ \/ ___|
| ' /  | | | | |_) |  _| |  \| | | | \___ \
| . \  | |_| |  _ <| |___| |\  | |_| |___) |
|_|\_\  \___/|_| \_\_____|_| \_|\___/|____/

       KAREN OS | Personal Assistant
"""


def run_terminal(
    assistant: Assistant,
    memory: ConversationStore,
    speech: SpeechOutput | None = None,
) -> None:
    print(BANNER)
    mode = "AI provider connected" if assistant.provider is not None else "offline demo mode"
    print(f"Status: {mode}")
    print("Commands: /help, /clear, /quit")

    while True:
        try:
            prompt = input("\nYOU > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nKAREN > Session closed.")
            break

        if not prompt:
            continue
        command = prompt.lower()
        if command in {"/quit", "/exit"}:
            print("KAREN > Session closed.")
            break
        if command == "/help":
            print("KAREN > Type a message to chat. /clear removes local history. /quit exits.")
            continue
        if command == "/clear":
            memory.clear()
            print("KAREN > Local conversation history cleared.")
            continue

        try:
            answer = assistant.respond(prompt)
            print(f"\nKAREN > {answer}")
            if speech is not None:
                speech.speak(answer)
        except Exception as exc:
            print(f"\nKAREN ERROR > {exc}")
