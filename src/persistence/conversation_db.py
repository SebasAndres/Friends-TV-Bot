"""SQLite-backed persistence for sessions and conversation messages."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from logging import getLogger

logger = getLogger(__name__)

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    character_name TEXT NOT NULL,
    emoji TEXT NOT NULL,
    color TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_active TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    tool_calls TEXT,
    tool_call_id TEXT,
    tool_name TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_messages_session
    ON messages(session_id, created_at);
"""


class ConversationDB:
    """Thin wrapper around a SQLite database for conversation persistence."""

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        logger.info("Conversation DB ready at %s", self._db_path)

    # ------------------------------------------------------------------
    # Session CRUD
    # ------------------------------------------------------------------

    def save_session(
        self,
        session_id: str,
        character_name: str,
        emoji: str,
        color: str,
    ) -> None:
        """Upsert session metadata."""
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO sessions (id, character_name, emoji, color, created_at, last_active) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET last_active = excluded.last_active",
            (session_id, character_name, emoji, color, now, now),
        )
        self._conn.commit()

    def load_sessions(self) -> list[dict]:
        """Return all persisted session metadata."""
        rows = self._conn.execute(
            "SELECT id, character_name, emoji, color, created_at, last_active "
            "FROM sessions ORDER BY last_active DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_session(self, session_id: str) -> None:
        """Remove a session and all its messages."""
        self._conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        self._conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self._conn.commit()

    def touch_session(self, session_id: str) -> None:
        """Update the last_active timestamp for a session."""
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE sessions SET last_active = ? WHERE id = ?",
            (now, session_id),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Message CRUD
    # ------------------------------------------------------------------

    def save_message(self, session_id: str, message: dict) -> None:
        """Persist a single message dict."""
        tool_calls_json = None
        if message.get("tool_calls"):
            tool_calls_json = json.dumps(message["tool_calls"])

        self._conn.execute(
            "INSERT INTO messages (session_id, role, content, tool_calls, tool_call_id, tool_name) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                session_id,
                message.get("role", ""),
                message.get("content", "") or "",
                tool_calls_json,
                message.get("tool_call_id"),
                message.get("name"),
            ),
        )
        self._conn.commit()

    def load_messages(
        self, session_id: str, limit: int = 50
    ) -> list[dict]:
        """Load recent messages for a session, oldest first."""
        rows = self._conn.execute(
            "SELECT role, content, tool_calls, tool_call_id, tool_name "
            "FROM messages WHERE session_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()

        messages: list[dict] = []
        for row in reversed(rows):
            msg: dict = {"role": row["role"], "content": row["content"]}
            if row["tool_calls"]:
                msg["tool_calls"] = json.loads(row["tool_calls"])
            if row["tool_call_id"]:
                msg["tool_call_id"] = row["tool_call_id"]
            if row["tool_name"]:
                msg["name"] = row["tool_name"]
            messages.append(msg)
        return messages

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
