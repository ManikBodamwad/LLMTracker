"""
Context helpers and global feature tracking context manager.
"""

from __future__ import annotations

import threading
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from llmtrack.tracker import CostTracker

# The active feature tag. A ContextVar (rather than threading.local) gives each
# asyncio task its own value, so concurrent requests on one event loop cannot
# tag each other's calls; threads still start with no feature set.
_CURRENT_FEATURE: ContextVar[Optional[str]] = ContextVar(
    "llmtrack_current_feature", default=None
)

_DEFAULT_TRACKER: Optional[CostTracker] = None
_INIT_LOCK = threading.Lock()


def get_current_feature() -> Optional[str]:
    """Return the feature tag active in the current thread/task, if any."""
    return _CURRENT_FEATURE.get()


@contextmanager
def use_feature(name: str) -> Generator[None, None, None]:
    """Tag the current thread/task with ``name`` for the duration of the block."""
    previous = _CURRENT_FEATURE.get()
    token = _CURRENT_FEATURE.set(name)
    try:
        yield
    finally:
        try:
            _CURRENT_FEATURE.reset(token)
        except ValueError:  # exited in a different Context than it was entered
            _CURRENT_FEATURE.set(previous)


def get_default_tracker() -> CostTracker:
    """Return the default global CostTracker instance."""
    global _DEFAULT_TRACKER
    if _DEFAULT_TRACKER is None:
        with _INIT_LOCK:
            if _DEFAULT_TRACKER is None:
                from llmtrack.tracker import CostTracker

                _DEFAULT_TRACKER = CostTracker()
    return _DEFAULT_TRACKER


@contextmanager
def feature(name: str) -> Generator[None, None, None]:
    """
    Context manager to tag LLM calls with a feature name
    using the default global CostTracker.

    Usage:
        from llmtrack import feature

        with feature("document_summarization"):
            response = openai.chat.completions.create(...)
    """
    tracker = get_default_tracker()
    with tracker.feature(name):
        yield
