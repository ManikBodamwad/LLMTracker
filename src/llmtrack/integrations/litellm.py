"""
Patches the LiteLLM library to automatically intercept
all completion calls and log them to the tracker.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from llmtrack.tracker import CostTracker


def patch_litellm(tracker: CostTracker) -> None:
    """
    Patch LiteLLM or register callbacks to track calls.
    """
    try:
        import litellm
    except ImportError:
        return

    try:
        if hasattr(litellm, "completion"):
            original_completion = litellm.completion

            def patched_completion(*args: Any, **kwargs: Any) -> Any:
                start = time.time()
                response = original_completion(*args, **kwargs)
                latency_ms = (time.time() - start) * 1000

                try:
                    model = kwargs.get("model", "unknown")
                    usage = getattr(response, "usage", None)
                    if usage:
                        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
                        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
                        tracker.log_call(
                            model=model,
                            input_tokens=prompt_tokens,
                            output_tokens=completion_tokens,
                            latency_ms=latency_ms,
                        )
                except Exception:
                    pass

                return response

            litellm.completion = patched_completion
    except Exception:
        pass
