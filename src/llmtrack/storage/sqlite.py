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

_COLUMNS = (
    "id, feature, model, provider, input_tokens, output_tokens, total_tokens, "
    "cost_usd, latency_ms, timestamp, metadata, "
    "cached_input_tokens, cache_creation_tokens, estimated_pricing"
)

# Columns added after 0.3.x; existing databases are migrated on open.
_MIGRATIONS = {
    "cached_input_tokens": "INTEGER NOT NULL DEFAULT 0",
    "cache_creation_tokens": "INTEGER NOT NULL DEFAULT 0",
    "estimated_pricing": "INTEGER NOT NULL DEFAULT 0",
}


def _utc_iso(ts: datetime) -> str:
    """Normalize to UTC ISO-8601 so string comparison matches time order."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat()


class SQLiteStorage(BaseStorage):
    """
    Stores call events in a local SQLite database.
    File is created at db_path on first use.
    Default: llmtrack.db in current directory.

    A short-lived connection is opened per operation, which keeps the backend
    safe across threads and forked worker processes. The database uses WAL
    journaling and a busy timeout so concurrent writers wait instead of failing.
    """

    def __init__(self, db_path: Union[str, Path] = "llmtrack.db"):
        self.db_path = Path(db_path)
        if self.db_path.parent and not self.db_path.parent.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn() as conn:
            try:
                conn.execute("PRAGMA journal_mode=WAL")
            except sqlite3.OperationalError:
                pass  # e.g. filesystems without shared-memory support
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
            existing = {
                row[1] for row in conn.execute("PRAGMA table_info(call_events)")
            }
            for column, ddl in _MIGRATIONS.items():
                if column not in existing:
                    conn.execute(f"ALTER TABLE call_events ADD COLUMN {column} {ddl}")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_feature ON call_events(feature)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON call_events(timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_feature_timestamp "
                "ON call_events(feature, timestamp)"
            )

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save(self, event: CallEvent) -> None:
        with self._conn() as conn:
            conn.execute(
                f"INSERT INTO call_events ({_COLUMNS}) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
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
                    _utc_iso(event.timestamp),
                    json.dumps(event.metadata),
                    event.cached_input_tokens,
                    event.cache_creation_tokens,
                    int(event.estimated_pricing),
                ),
            )

    def query(self, days: float = 7) -> List[CallEvent]:
        """Return CallEvent list for the last N days."""
        from llmtrack.tracker import CallEvent

        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT {_COLUMNS}
                FROM call_events
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """,
                (self._cutoff(days),),
            ).fetchall()

        return [
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
                cached_input_tokens=row[11],
                cache_creation_tokens=row[12],
                estimated_pricing=bool(row[13]),
            )
            for row in rows
        ]

    def feature_cost(self, feature: str, days: float = 1.0) -> float:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM call_events "
                "WHERE feature = ? AND timestamp >= ?",
                (feature, self._cutoff(days)),
            ).fetchone()
        return float(row[0])

    def clear(self) -> None:
        """Delete all stored events."""
        with self._conn() as conn:
            conn.execute("DELETE FROM call_events")

    @staticmethod
    def _cutoff(days: float) -> str:
        return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
