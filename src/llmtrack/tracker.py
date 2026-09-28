"""
Core tracker module for llmtrack.
"""

from __future__ import annotations

import logging
import uuid
import warnings
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from llmtrack.context import get_current_feature, use_feature
from llmtrack.pricing.models import estimate_cost
from llmtrack.pricing.providers import infer_provider as _infer_provider
from llmtrack.storage.base import BaseStorage
from llmtrack.storage.sqlite import SQLiteStorage

logger = logging.getLogger("llmtrack")

# Models already warned about for falling back to estimated pricing.
_WARNED_MODELS: Set[str] = set()


class CallEvent(BaseModel):
    """Represents a single LLM API call with cost attribution."""

    id: str
    feature: str
    model: str
    provider: str  # "openai", "anthropic", "google", "mistral", "open_source", "other"
    input_tokens: int  # total prompt tokens, including cached / cache-creation
    output_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float = 0.0
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    cached_input_tokens: int = 0  # subset of input_tokens read from a prompt cache
    cache_creation_tokens: int = 0  # subset of input_tokens written to a cache
    # True when cost_usd used fuzzy-matched or fallback pricing (unknown model).
    estimated_pricing: bool = False


class CostTracker:
    """
    Main class for tracking LLM costs per feature.

    Usage:
        tracker = CostTracker()

        with tracker.feature("document_summarization"):
            response = openai.chat.completions.create(...)

        tracker.report()
    """

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        db_path: str = "llmtrack.db",
        auto_patch: bool = True,
        inject_stream_usage: bool = True,
    ):
        """
        Args:
            storage: Storage backend. Defaults to SQLiteStorage.
            db_path: Path for SQLite database file. Default: "llmtrack.db"
            auto_patch: If True, automatically patches installed OpenAI,
                        Anthropic and LiteLLM clients to intercept calls.
                        Default: True
            inject_stream_usage: If True, streaming OpenAI/LiteLLM calls that
                        don't set ``stream_options`` get
                        ``{"include_usage": True}`` so token usage is reported
                        (the API then sends one extra final chunk with an empty
                        ``choices`` list). Default: True
        """
        self.storage = storage or SQLiteStorage(db_path=db_path)
        self.inject_stream_usage = inject_stream_usage
        self._has_alerts = False

        if auto_patch:
            self._apply_patches()

    @property
    def _current_feature(self) -> Optional[str]:
        return get_current_feature()

    @contextmanager
    def feature(self, name: str) -> Generator[None, None, None]:
        """
        Context manager to tag all LLM calls within the block
        with a feature name. Safe across threads and asyncio tasks.

        Usage:
            with tracker.feature("summarization"):
                response = openai.chat.completions.create(...)
        """
        with use_feature(name):
            yield

    def unpatch(self) -> None:
        """Stop this tracker from receiving calls from the patched SDKs."""
        from llmtrack.integrations._base import unregister_tracker

        unregister_tracker(self)

    def log_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        feature: Optional[str] = None,
        latency_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        cached_input_tokens: int = 0,
        cache_creation_tokens: int = 0,
    ) -> CallEvent:
        """
        Manually log an LLM call.

        ``input_tokens`` is the total prompt size; pass ``cached_input_tokens``
        / ``cache_creation_tokens`` for the portions billed at cache rates.

        Use this if auto_patch doesn't work for your setup,
        or if you want explicit control.

        Usage:
            event = tracker.log_call(
                model="gpt-4o",
                input_tokens=500,
                output_tokens=200,
                feature="customer_support",
            )
        """
        feature_name = feature or self._current_feature or "untagged"
        provider = _infer_provider(model)
        estimate = estimate_cost(
            model,
            input_tokens,
            output_tokens,
            cached_input_tokens=cached_input_tokens,
            cache_creation_tokens=cache_creation_tokens,
        )
        if estimate.estimated and model not in _WARNED_MODELS:
            _WARNED_MODELS.add(model)
            warnings.warn(
                f"llmtrack: no exact pricing for model {model!r}; cost is "
                "estimated. Register it with "
                "llmtrack.pricing.updater.register_custom_model().",
                stacklevel=2,
            )
        total_tokens = input_tokens + output_tokens

        event = CallEvent(
            id=str(uuid.uuid4()),
            feature=feature_name,
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=estimate.cost_usd,
            latency_ms=latency_ms,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {},
            cached_input_tokens=cached_input_tokens,
            cache_creation_tokens=cache_creation_tokens,
            estimated_pricing=estimate.estimated,
        )
        self.storage.save(event)
        if self._has_alerts:
            self._check_alerts(feature_name)
        return event

    def _check_alerts(self, feature_name: str) -> None:
        """Evaluate budget alerts for a feature; never let them break tracking."""
        from llmtrack.report.alerts import AlertManager

        try:
            AlertManager.check_feature(self.storage, feature_name)
        except Exception:
            logger.warning("llmtrack budget alert check failed", exc_info=True)

    def report(
        self,
        days: int = 7,
        output: str = "terminal",
        filepath: Optional[str] = None,
    ) -> None:
        """
        Generate a cost breakdown report.

        Args:
            days: Number of past days to include. Default: 7
            output: "terminal" for rich table, "html" for HTML file
            filepath: Path for HTML output. Required if output="html"

        Usage:
            tracker.report()                          # terminal, last 7 days
            tracker.report(days=30)                   # terminal, last 30 days
            tracker.report(output="html",
                           filepath="report.html")    # HTML report
        """
        from rich.console import Console

        from llmtrack.report.cli import print_report
        from llmtrack.report.html import generate_html_report

        events = self.storage.query(days=days)

        if output == "terminal":
            print_report(events, days=days)
        elif output == "html":
            if not filepath:
                filepath = f"llmtrack_report_{days}d.html"
            generate_html_report(events, filepath=filepath, days=days)
            Console().print(f"[green]Report saved to: {filepath}[/green]")
        else:
            raise ValueError(
                f"Unknown output format: {output}. Use 'terminal' or 'html'."
            )

    def set_budget_alert(
        self,
        feature: str,
        daily_limit_usd: float,
        callback: Optional[Callable[[str, float, float], None]] = None,
    ) -> None:
        """
        Set a daily budget alert for a feature.

        Spend over the last 24 hours is checked after every tracked call. When
        it reaches the limit, a warning is printed (or ``callback`` is called
        if provided), at most once per UTC day per alert.

        Args:
            feature: Feature name to monitor
            daily_limit_usd: Daily spending limit in USD
            callback: Optional function called with (feature, spent, limit)
                      when limit is exceeded
        """
        from llmtrack.report.alerts import AlertManager

        AlertManager.register(
            storage=self.storage,
            feature=feature,
            daily_limit_usd=daily_limit_usd,
            callback=callback,
        )
        self._has_alerts = True

    def summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Return cost summary as a dict for programmatic use.

        Returns:
            {
                "total_cost_usd": 30.50,
                "total_calls": 39650,
                "estimated_calls": 0,  # calls priced with fuzzy/fallback rates
                "features": {
                    "document_summary": {
                        "cost_usd": 12.40,
                        "calls": 1240,
                        "avg_cost_per_call": 0.010,
                        "input_tokens": 500000,
                        "output_tokens": 200000,
                        "estimated_calls": 0,
                    },
                    ...
                },
                "period_days": 7,
            }
        """
        events = self.storage.query(days=days)
        return _aggregate(events, days=days)

    def _apply_patches(self) -> None:
        """Auto-patch whichever of the OpenAI, Anthropic and LiteLLM SDKs are installed."""
        from llmtrack.integrations.anthropic import patch_anthropic
        from llmtrack.integrations.litellm import patch_litellm
        from llmtrack.integrations.openai import patch_openai

        for name, patch in (
            ("openai", patch_openai),
            ("anthropic", patch_anthropic),
            ("litellm", patch_litellm),
        ):
            try:
                patch(self)
            except Exception:
                logger.warning("llmtrack could not patch %s", name, exc_info=True)


def _aggregate(events: List[CallEvent], days: int) -> Dict[str, Any]:
    """Aggregate CallEvents into summary dict."""
    features: Dict[str, Dict[str, Any]] = {}
    total_cost = 0.0
    total_calls = 0
    estimated_calls = 0

    for event in events:
        f = event.feature
        if f not in features:
            features[f] = {
                "cost_usd": 0.0,
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "estimated_calls": 0,
            }
        features[f]["cost_usd"] += event.cost_usd
        features[f]["calls"] += 1
        if event.estimated_pricing:
            features[f]["estimated_calls"] += 1
            estimated_calls += 1
        features[f]["input_tokens"] += event.input_tokens
        features[f]["output_tokens"] += event.output_tokens
        total_cost += event.cost_usd
        total_calls += 1

    for f in features:
        calls = features[f]["calls"]
        features[f]["avg_cost_per_call"] = (
            features[f]["cost_usd"] / calls if calls > 0 else 0.0
        )
        features[f]["cost_usd"] = round(features[f]["cost_usd"], 8)

    return {
        "total_cost_usd": round(total_cost, 6),
        "total_calls": total_calls,
        "estimated_calls": estimated_calls,
        "features": features,
        "period_days": days,
    }
