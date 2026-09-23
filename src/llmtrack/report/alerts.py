"""
Budget alert system.
Checks daily spend per feature and triggers warnings or callbacks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from rich.console import Console

if TYPE_CHECKING:
    from llmtrack.storage.base import BaseStorage

console = Console()


class AlertManager:
    """Manager for registering and checking feature budget alerts."""

    _alerts: List[Dict[str, Any]] = []

    @classmethod
    def register(
        cls,
        storage: BaseStorage,
        feature: str,
        daily_limit_usd: float,
        callback: Optional[Callable[[str, float, float], None]] = None,
    ) -> None:
        """Register a feature budget threshold."""
        # Replace existing alert for this feature/storage if already registered
        cls._alerts = [
            a
            for a in cls._alerts
            if not (a["storage"] == storage and a["feature"] == feature)
        ]
        cls._alerts.append(
            {
                "storage": storage,
                "feature": feature,
                "daily_limit_usd": float(daily_limit_usd),
                "callback": callback,
            }
        )

    @classmethod
    def check_all(cls) -> List[Dict[str, Any]]:
        """
        Check all registered alerts against the last 24h of data.
        Returns a list of triggered alert dictionaries.
        """
        triggered = []
        for alert in list(cls._alerts):
            storage = alert["storage"]
            feature_name = alert["feature"]
            limit = alert["daily_limit_usd"]
            callback = alert["callback"]

            events = storage.query(days=1)
            feature_events = [e for e in events if e.feature == feature_name]
            spent = sum(e.cost_usd for e in feature_events)

            if spent >= limit:
                triggered.append(
                    {
                        "feature": feature_name,
                        "spent_usd": spent,
                        "limit_usd": limit,
                    }
                )
                if callback:
                    try:
                        callback(feature_name, spent, limit)
                    except Exception:
                        pass
                else:
                    console.print(
                        f"[bold red][llmtrack ALERT][/bold red] "
                        f"Feature '[bold yellow]{feature_name}[/bold yellow]' "
                        f"spent [bold red]${spent:.4f}[/bold red] today "
                        f"(limit: ${limit:.4f})"
                    )
        return triggered

    @classmethod
    def clear(cls) -> None:
        """Clear all registered alerts."""
        cls._alerts.clear()
