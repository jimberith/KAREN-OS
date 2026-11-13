"""SQLite-backed conversation history and user-controlled notes."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def database_path() -> Path:
    override = os.getenv("KAREN_DATA_DIR", "").strip()
    base = Path(override).expanduser() if override else Path(__file__).resolve().parents[4] / "data"
    base.mkdir(parents=True, exist_ok=True)
    return base / "karenos.sqlite3"


class MemoryStore:
    """Persistent local memory. No cloud database or third-party memory service is used."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                """CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            db.execute(
                """CREATE INDEX IF NOT EXISTS idx_messages_session
                   ON messages(session_id, id)"""
            )
            db.execute(
                """CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            db.execute(
                """CREATE INDEX IF NOT EXISTS idx_notes_session
                   ON notes(session_id, id)"""
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def save_exchange(self, session_id: str, user_text: str, assistant_text: str) -> None:
        now = self._now()
        with self._connect() as db:
            db.executemany(
                "INSERT INTO messages(session_id, role, content, created_at) VALUES(?,?,?,?)",
                [
                    (session_id, "user", user_text, now),
                    (session_id, "assistant", assistant_text, now),
                ],
            )

    def history(self, session_id: str, limit: int = 60) -> list[dict[str, str]]:
        with self._connect() as db:
            rows = db.execute(
                """SELECT role, content, created_at FROM messages
                   WHERE session_id=? ORDER BY id DESC LIMIT ?""",
                (session_id, min(max(limit, 1), 100)),
            ).fetchall()
        return [
            {"role": row["role"], "content": row["content"], "created_at": row["created_at"]}
            for row in reversed(rows)
        ]

    def clear_history(self, session_id: str) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM messages WHERE session_id=?", (session_id,))

    def remember(self, session_id: str, content: str, title: str = "") -> int:
        content = content.strip()
        if not content:
            raise ValueError("A memory note cannot be empty.")
        title = title.strip()[:120] or content[:80]
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO notes(session_id, title, content, created_at) VALUES(?,?,?,?)",
                (session_id, title, content, self._now()),
            )
            return int(cursor.lastrowid)

    def search_notes(self, session_id: str, query: str = "", limit: int = 8) -> list[dict[str, Any]]:
        query = query.strip()
        with self._connect() as db:
            if query:
                terms = [term for term in query.split() if len(term) > 2][:6]
                if terms:
                    conditions = " OR ".join("(title LIKE ? OR content LIKE ?)" for _ in terms)
                    parameters: list[str | int] = [session_id]
                    for term in terms:
                        parameters.extend((f"%{term}%", f"%{term}%"))
                    parameters.append(min(max(limit, 1), 20))
                    rows = db.execute(
                        f"""SELECT id, title, content, created_at FROM notes
                            WHERE session_id=? AND ({conditions})
                            ORDER BY id DESC LIMIT ?""",
                        parameters,
                    ).fetchall()
                else:
                    rows = []
            else:
                rows = db.execute(
                    """SELECT id, title, content, created_at FROM notes
                       WHERE session_id=? ORDER BY id DESC LIMIT ?""",
                    (session_id, min(max(limit, 1), 20)),
                ).fetchall()
        return [dict(row) for row in rows]

    def delete_note(self, session_id: str, note_id: int) -> bool:
        with self._connect() as db:
            cursor = db.execute(
                "DELETE FROM notes WHERE id=? AND session_id=?",
                (note_id, session_id),
            )
            return cursor.rowcount > 0
