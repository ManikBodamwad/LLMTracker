"""
Context helpers and global feature tracking context manager.
"""

from __future__ import annotations

import threading
from collections.abc import Generator
from contextlib import contextmanager

_DEFAULT_TRACKER = None
_INIT_LOCK = threading.Lock()


def get_default_tracker():
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
