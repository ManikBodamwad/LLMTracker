"""
Budget alert system.
Checks rolling 24h spend per feature and triggers warnings or callbacks.
"""

from __future__ import annotations

import logging
import threading
import weakref
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from rich.console import Console

if TYPE_CHECKING:
    from llmtrack.storage.base import BaseStorage

console = Console()
logger = logging.getLogger("llmtrack")


def _today() -> date:
    return datetime.now(timezone.utc).date()


class AlertManager:
    """
    Manager for registering and checking feature budget alerts.

    ``CostTracker.log_call`` calls :meth:`check_feature` after saving each
    event, so alerts fire as spend crosses the limit. Each alert notifies at
    most once per UTC day; :meth:`check_all` still reports every alert that is
    currently over its limit.
    """

    _alerts: List[Dict[str, Any]] = []
    _lock = threading.RLock()

    @classmethod
    def register(
        cls,
        storage: BaseStorage,
        feature: str,
        daily_limit_usd: float,
        callback: Optional[Callable[[str, float, float], None]] = None,
    ) -> None:
        """Register a feature budget threshold."""
        with cls._lock:
            # Replace existing alert for this feature/storage if already registered
            cls._prune()
            cls._alerts = [
                a
                for a in cls._alerts
                if not (a["storage_ref"]() is storage and a["feature"] == feature)
            ]
            cls._alerts.append(
                {
                    "storage_ref": weakref.ref(storage),
                    "feature": feature,
                    "daily_limit_usd": float(daily_limit_usd),
                    "callback": callback,
                    "notified_on": None,
                }
            )

    @classmethod
    def check_feature(cls, storage: BaseStorage, feature: str) -> List[Dict[str, Any]]:
        """Check alerts registered for ``feature`` on ``storage``."""
        with cls._lock:
            alerts = [
                a
                for a in cls._alerts
                if a["feature"] == feature and a["storage_ref"]() is storage
            ]
        return cls._check(alerts)

    @classmethod
    def check_all(cls) -> List[Dict[str, Any]]:
        """
        Check all registered alerts against the last 24h of data.
        Returns a list of the alerts currently over their limit.
        """
        with cls._lock:
            cls._prune()
            alerts = list(cls._alerts)
        return cls._check(alerts)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered alerts."""
        with cls._lock:
            cls._alerts = []

    @classmethod
    def _prune(cls) -> None:
        cls._alerts = [a for a in cls._alerts if a["storage_ref"]() is not None]

    @classmethod
    def _check(cls, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        triggered = []
        for alert in alerts:
            storage = alert["storage_ref"]()
            if storage is None:
                continue
            feature_name = alert["feature"]
            limit = alert["daily_limit_usd"]

            spent = storage.feature_cost(feature_name, days=1)
            if spent < limit:
                continue

            triggered.append(
                {"feature": feature_name, "spent_usd": spent, "limit_usd": limit}
            )

            with cls._lock:
                today = _today()
                if alert["notified_on"] == today:
                    continue
                alert["notified_on"] = today
            cls._notify(alert["callback"], feature_name, spent, limit)
        return triggered

    @staticmethod
    def _notify(
        callback: Optional[Callable[[str, float, float], None]],
        feature_name: str,
        spent: float,
        limit: float,
    ) -> None:
        if callback:
            try:
                callback(feature_name, spent, limit)
            except Exception:
                logger.warning(
                    "llmtrack budget alert callback for %r raised",
                    feature_name,
                    exc_info=True,
                )
        else:
            console.print(
                f"[bold red][llmtrack ALERT][/bold red] "
                f"Feature '[bold yellow]{feature_name}[/bold yellow]' "
                f"spent [bold red]${spent:.4f}[/bold red] today "
                f"(limit: ${limit:.4f})"
            )
