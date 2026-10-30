from karenos.brain.assistant import Assistant
from karenos.config import Settings
from karenos.memory.store import ConversationStore


class FakeProvider:
    def __init__(self):
        self.received = None

    def reply(self, messages):
        self.received = messages
        return "A test response."


def test_offline_assistant_saves_exchange(tmp_path):
    memory = ConversationStore(tmp_path / "history.json")
    assistant = Assistant(Settings(data_dir=tmp_path), memory)

    answer = assistant.respond("Hello KAREN")

    assert "offline demo mode" in answer
    records = memory.load()
    assert len(records) == 2
    assert records[0]["role"] == "user"
    assert records[0]["content"] == "Hello KAREN"
    assert records[1]["role"] == "assistant"


def test_provider_receives_prompt_and_returns_answer(tmp_path):
    memory = ConversationStore(tmp_path / "history.json")
    provider = FakeProvider()
    assistant = Assistant(Settings(data_dir=tmp_path), memory, provider=provider)

    assert assistant.respond("What time is it?") == "A test response."
    assert provider.received[-1] == {"role": "user", "content": "What time is it?"}


def test_assistant_rejects_blank_prompt(tmp_path):
    assistant = Assistant(
        Settings(data_dir=tmp_path),
        ConversationStore(tmp_path / "history.json"),
    )
    with pytest.raises(ValueError):
        assistant.respond("   ")


import pytest
