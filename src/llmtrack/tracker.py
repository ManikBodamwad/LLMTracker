"""
Core tracker module for llmtrack.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from llmtrack.pricing.models import get_cost
from llmtrack.storage.base import BaseStorage
from llmtrack.storage.sqlite import SQLiteStorage


class CallEvent(BaseModel):
    """Represents a single LLM API call with cost attribution."""

    id: str
    feature: str
    model: str
    provider: str  # "openai", "anthropic", "google", "mistral", "open_source", "other"
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float = 0.0
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
    ):
        """
        Args:
            storage: Storage backend. Defaults to SQLiteStorage.
            db_path: Path for SQLite database file. Default: "llmtrack.db"
            auto_patch: If True, automatically patches OpenAI and Anthropic
                        clients to intercept calls. Default: True
        """
        self.storage = storage or SQLiteStorage(db_path=db_path)
        self._local = threading.local()

        if auto_patch:
            self._apply_patches()

    @property
    def _current_feature(self) -> Optional[str]:
        return getattr(self._local, "feature", None)

    @_current_feature.setter
    def _current_feature(self, value: Optional[str]) -> None:
        self._local.feature = value

    @contextmanager
    def feature(self, name: str) -> Generator[None, None, None]:
        """
        Context manager to tag all LLM calls within the block
        with a feature name.

        Usage:
            with tracker.feature("summarization"):
                response = openai.chat.completions.create(...)
        """
        previous = self._current_feature
        self._current_feature = name
        try:
            yield
        finally:
            self._current_feature = previous

    def log_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        feature: Optional[str] = None,
        latency_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CallEvent:
        """
        Manually log an LLM call.

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
        cost = get_cost(
            model=model, input_tokens=input_tokens, output_tokens=output_tokens
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
            cost_usd=cost,
            latency_ms=latency_ms,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        self.storage.save(event)
        return event

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

        If daily spend for that feature exceeds the limit,
        a warning is printed (or callback is called if provided).

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

    def summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Return cost summary as a dict for programmatic use.

        Returns:
            {
                "total_cost_usd": 30.50,
                "total_calls": 39650,
                "features": {
                    "document_summary": {
                        "cost_usd": 12.40,
                        "calls": 1240,
                        "avg_cost_per_call": 0.010,
                        "input_tokens": 500000,
                        "output_tokens": 200000,
                    },
                    ...
                },
                "period_days": 7,
            }
        """
        events = self.storage.query(days=days)
        return _aggregate(events, days=days)

    def _apply_patches(self) -> None:
        """Auto-patch OpenAI, Anthropic, and LiteLLM clients."""
        try:
            from llmtrack.integrations.openai import patch_openai

            patch_openai(self)
        except Exception:
            pass

        try:
            from llmtrack.integrations.anthropic import patch_anthropic

            patch_anthropic(self)
        except Exception:
            pass

        try:
            from llmtrack.integrations.litellm import patch_litellm

            patch_litellm(self)
        except Exception:
            pass


def _infer_provider(model: str) -> str:
    """Infer provider name from model string."""
    model_lower = model.lower()
    if any(
        x in model_lower
        for x in ["gpt", "o1", "o3", "o4", "text-davinci", "text-embedding"]
    ):
        return "openai"
    elif any(x in model_lower for x in ["claude"]):
        return "anthropic"
    elif any(x in model_lower for x in ["gemini"]):
        return "google"
    elif any(x in model_lower for x in ["grok"]):
        return "xai"
    elif any(x in model_lower for x in ["deepseek"]):
        return "deepseek"
    elif any(
        x in model_lower
        for x in ["mistral", "mixtral", "codestral", "ministral", "pixtral"]
    ):
        return "mistral"
    elif any(x in model_lower for x in ["command", "cohere", "embed-"]):
        return "cohere"
    elif any(x in model_lower for x in ["qwen"]):
        return "alibaba"
    elif any(x in model_lower for x in ["llama"]):
        return "meta"
    return "other"


def _aggregate(events: List[CallEvent], days: int) -> Dict[str, Any]:
    """Aggregate CallEvents into summary dict."""
    features: Dict[str, Dict[str, Any]] = {}
    total_cost = 0.0
    total_calls = 0

    for event in events:
        f = event.feature
        if f not in features:
            features[f] = {
                "cost_usd": 0.0,
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
            }
        features[f]["cost_usd"] += event.cost_usd
        features[f]["calls"] += 1
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
        "features": features,
        "period_days": days,
    }
