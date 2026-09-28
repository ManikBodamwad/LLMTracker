"""
In-memory storage backend.
Use for testing or short-lived scripts.
Data is lost when process exits.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, List

from llmtrack.storage.base import BaseStorage

if TYPE_CHECKING:
    from llmtrack.tracker import CallEvent


def _aware(ts: datetime) -> datetime:
    """Treat naive timestamps as UTC."""
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


class MemoryStorage(BaseStorage):
    """Thread-safe in-memory storage."""

    def __init__(self) -> None:
        self._events: List[CallEvent] = []
        self._lock = threading.Lock()

    def save(self, event: CallEvent) -> None:
        with self._lock:
            self._events.append(event)

    def query(self, days: float = 7) -> List[CallEvent]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        with self._lock:
            return [e for e in self._events if _aware(e.timestamp) >= cutoff]

    def feature_cost(self, feature: str, days: float = 1.0) -> float:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        with self._lock:
            return sum(
                e.cost_usd
                for e in self._events
                if e.feature == feature and _aware(e.timestamp) >= cutoff
            )

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
