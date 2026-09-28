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
    def query(self, days: float = 7) -> List[CallEvent]:
        """Retrieve events from the last N days."""

    @abstractmethod
    def clear(self) -> None:
        """Delete all stored events."""

    def feature_cost(self, feature: str, days: float = 1.0) -> float:
        """
        Total cost in USD for ``feature`` over the last ``days`` days.

        The default implementation scans ``query()``; backends should override
        it with something cheaper (budget alerts call it on every tracked call).
        """
        return sum(e.cost_usd for e in self.query(days=days) if e.feature == feature)
