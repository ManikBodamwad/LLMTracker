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


class MemoryStorage(BaseStorage):
    """Thread-safe in-memory storage."""

    def __init__(self) -> None:
        self._events: List[CallEvent] = []
        self._lock = threading.Lock()

    def save(self, event: CallEvent) -> None:
        with self._lock:
            self._events.append(event)

    def query(self, days: int = 7) -> List[CallEvent]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        with self._lock:
            return [
                e
                for e in self._events
                if (
                    e.timestamp
                    if e.timestamp.tzinfo
                    else e.timestamp.replace(tzinfo=timezone.utc)
                )
                >= cutoff
            ]

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
