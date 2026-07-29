from __future__ import annotations

import asyncio
import json
import sqlite3
from collections import defaultdict
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from jarvis_agent.domain.models import RuntimeEvent


class EventStore:
    """Append-only SQLite timeline plus in-process fan-out."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._subscribers: dict[str, set[asyncio.Queue[RuntimeEvent]]] = defaultdict(set)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _init_db(self) -> None:
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT NOT NULL UNIQUE,
                    session_id TEXT NOT NULL,
                    meeting_session_id TEXT,
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_events_session_sequence
                  ON events(session_id, sequence);

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS approvals (
                    id TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS wake_samples (
                    id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    phrase_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    feature_json TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    false_wake INTEGER NOT NULL DEFAULT 0
                );
                """
            )

    async def append(self, event: RuntimeEvent) -> RuntimeEvent:
        async with self._lock:
            with self._connect() as con:
                cursor = con.execute(
                    """
                    INSERT INTO events(
                      id, session_id, meeting_session_id, event_type, occurred_at,
                      correlation_id, source, version, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.id,
                        event.session_id,
                        event.meeting_session_id,
                        event.event_type,
                        event.occurred_at.isoformat(),
                        event.correlation_id,
                        event.source,
                        event.version,
                        json.dumps(event.payload, ensure_ascii=False, default=str),
                    ),
                )
                sequence = int(cursor.lastrowid)
            persisted = event.model_copy(update={"sequence": sequence})
        for queue in tuple(self._subscribers[event.session_id]):
            try:
                queue.put_nowait(persisted)
            except asyncio.QueueFull:
                # Slow clients can replay missed events from their cursor.
                pass
        return persisted

    def list_events(self, session_id: str, after: int = 0, limit: int = 1000) -> list[RuntimeEvent]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT * FROM events
                WHERE session_id = ? AND sequence > ?
                ORDER BY sequence ASC LIMIT ?
                """,
                (session_id, after, limit),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def latest_sequence(self, session_id: str) -> int:
        with self._connect() as con:
            row = con.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS seq FROM events WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return int(row["seq"])

    def list_sessions(self) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT session_id, MIN(occurred_at) AS created_at,
                       MAX(sequence) AS event_cursor, COUNT(*) AS event_count
                FROM events GROUP BY session_id ORDER BY created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    async def subscribe(self, session_id: str, after: int = 0) -> AsyncIterator[RuntimeEvent]:
        for event in self.list_events(session_id, after=after):
            yield event
        queue: asyncio.Queue[RuntimeEvent] = asyncio.Queue(maxsize=256)
        self._subscribers[session_id].add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers[session_id].discard(queue)

    def set_setting(self, key: str, value: Any) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO settings(key, value_json, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                  value_json=excluded.value_json,
                  updated_at=CURRENT_TIMESTAMP
                """,
                (key, json.dumps(value, ensure_ascii=False, default=str)),
            )

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._connect() as con:
            row = con.execute("SELECT value_json FROM settings WHERE key = ?", (key,)).fetchone()
        return default if row is None else json.loads(row["value_json"])

    def list_settings(self, prefix: str | None = None) -> dict[str, Any]:
        with self._connect() as con:
            if prefix is None:
                rows = con.execute("SELECT key, value_json FROM settings ORDER BY key").fetchall()
            else:
                rows = con.execute(
                    "SELECT key, value_json FROM settings WHERE key LIKE ? ORDER BY key",
                    (f"{prefix}%",),
                ).fetchall()
        return {row["key"]: json.loads(row["value_json"]) for row in rows}

    def delete_session(self, session_id: str) -> None:
        with self._connect() as con:
            con.execute("DELETE FROM events WHERE session_id = ?", (session_id,))

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> RuntimeEvent:
        return RuntimeEvent.model_validate(
            {
                "id": row["id"],
                "version": row["version"],
                "sequence": row["sequence"],
                "session_id": row["session_id"],
                "meeting_session_id": row["meeting_session_id"],
                "event_type": row["event_type"],
                "occurred_at": row["occurred_at"],
                "correlation_id": row["correlation_id"],
                "source": row["source"],
                "payload": json.loads(row["payload_json"]),
            }
        )
