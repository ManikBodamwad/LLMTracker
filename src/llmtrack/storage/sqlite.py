"""
SQLite-based persistent storage backend.
Default storage for llmtrack.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, List, Union

from llmtrack.storage.base import BaseStorage

if TYPE_CHECKING:
    from llmtrack.tracker import CallEvent


class SQLiteStorage(BaseStorage):
    """
    Stores call events in a local SQLite database.
    File is created at db_path on first use.
    Default: llmtrack.db in current directory.
    """

    def __init__(self, db_path: Union[str, Path] = "llmtrack.db"):
        self.db_path = Path(db_path)
        if self.db_path.parent and not self.db_path.parent.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS call_events (
                    id TEXT PRIMARY KEY,
                    feature TEXT NOT NULL,
                    model TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    latency_ms REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_feature ON call_events(feature)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON call_events(timestamp)"
            )

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path))
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save(self, event: CallEvent) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO call_events VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
                (
                    event.id,
                    event.feature,
                    event.model,
                    event.provider,
                    event.input_tokens,
                    event.output_tokens,
                    event.total_tokens,
                    event.cost_usd,
                    event.latency_ms,
                    event.timestamp.isoformat(),
                    json.dumps(event.metadata),
                ),
            )

    def query(self, days: int = 7) -> List[CallEvent]:
        """Return CallEvent list for the last N days."""
        from llmtrack.tracker import CallEvent

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, feature, model, provider, input_tokens, output_tokens,
                       total_tokens, cost_usd, latency_ms, timestamp, metadata
                FROM call_events
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """,
                (cutoff,),
            ).fetchall()

        events: List[CallEvent] = []
        for row in rows:
            events.append(
                CallEvent(
                    id=row[0],
                    feature=row[1],
                    model=row[2],
                    provider=row[3],
                    input_tokens=row[4],
                    output_tokens=row[5],
                    total_tokens=row[6],
                    cost_usd=row[7],
                    latency_ms=row[8],
                    timestamp=datetime.fromisoformat(row[9]),
                    metadata=json.loads(row[10]),
                )
            )
        return events

    def clear(self) -> None:
        """Delete all stored events."""
        with self._conn() as conn:
            conn.execute("DELETE FROM call_events")
