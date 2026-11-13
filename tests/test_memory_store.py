from karenos.web.features.memory import MemoryStore


def test_memory_is_session_scoped(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")
    store.remember("session-a", "Jim is building KAREN OS", "Project")
    store.remember("session-b", "Another user's private note", "Private")

    notes_a = store.search_notes("session-a")
    notes_b = store.search_notes("session-b")

    assert len(notes_a) == 1
    assert notes_a[0]["title"] == "Project"
    assert "Another user" not in str(notes_a)
    assert len(notes_b) == 1
    assert notes_b[0]["content"] == "Another user's private note"


def test_conversation_history_persists_and_can_be_cleared(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")
    store.save_exchange("one", "Hello", "Hello back")

    assert [x["role"] for x in store.history("one")] == ["user", "assistant"]
    store.clear_history("one")
    assert store.history("one") == []


def test_note_can_be_deleted(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")
    note_id = store.remember("session", "Keep this note")
    assert store.delete_note("session", note_id) is True
    assert store.search_notes("session") == []
