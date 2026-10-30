import pytest

from karenos.memory.store import ConversationStore


def test_store_appends_and_clears(tmp_path):
    store = ConversationStore(tmp_path / "chat.json")
    store.append("user", "Hello")
    store.append("assistant", "Hello there")

    records = store.load()
    assert [item["role"] for item in records] == ["user", "assistant"]
    assert records[0]["content"] == "Hello"
    assert "timestamp" in records[0]

    store.clear()
    assert store.load() == []


def test_store_rejects_invalid_role_and_empty_content(tmp_path):
    store = ConversationStore(tmp_path / "chat.json")
    with pytest.raises(ValueError):
        store.append("robot", "Hello")
    with pytest.raises(ValueError):
        store.append("user", "  ")


def test_store_reports_corrupt_json(tmp_path):
    path = tmp_path / "chat.json"
    store = ConversationStore(path)
    path.write_text("{", encoding="utf-8")
    with pytest.raises(RuntimeError):
        store.load()
