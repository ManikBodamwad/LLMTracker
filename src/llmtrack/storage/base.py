"""
Abstract base class for storage backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from llmtrack.tracker import CallEvent


class BaseStorage(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def save(self, event: CallEvent) -> None:
        """Persist a single call event."""

    @abstractmethod
    def query(self, days: int = 7) -> List[CallEvent]:
        """Retrieve events from the last N days."""

    @abstractmethod
    def clear(self) -> None:
        """Delete all stored events."""
