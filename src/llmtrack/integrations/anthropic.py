"""
Patches the Anthropic Python SDK to automatically intercept
all messages.create calls and log them to the tracker.

Supports both sync and async clients.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from llmtrack.tracker import CostTracker


def patch_anthropic(tracker: CostTracker) -> None:
    """
    Patch the Anthropic SDK to auto-track all message completions.
    Called automatically when CostTracker(auto_patch=True).
    """
    try:
        import anthropic as anthropic_sdk
    except ImportError:
        return

    # Patch sync messages.create
    try:
        resources = getattr(anthropic_sdk, "resources", None)
        msg_res = getattr(resources, "messages", None) if resources else None
        if msg_res is not None:
            cls_messages = getattr(msg_res, "Messages", None)
            if cls_messages is not None:
                original_sync_create = cls_messages.create

                def patched_sync_create(
                    self_inner: Any, *args: Any, **kwargs: Any
                ) -> Any:
                    start = time.time()
                    response = original_sync_create(self_inner, *args, **kwargs)
                    latency_ms = (time.time() - start) * 1000

                    try:
                        model = kwargs.get("model", "unknown")
                        usage = getattr(response, "usage", None)
                        if usage:
                            tracker.log_call(
                                model=model,
                                input_tokens=getattr(usage, "input_tokens", 0) or 0,
                                output_tokens=getattr(usage, "output_tokens", 0) or 0,
                                latency_ms=latency_ms,
                            )
                    except Exception:
                        pass

                    return response

                cls_messages.create = patched_sync_create  # type: ignore[method-assign,assignment]

            cls_async_messages = getattr(msg_res, "AsyncMessages", None)
            if cls_async_messages is not None:
                original_async_create = cls_async_messages.create

                async def patched_async_create(
                    self_inner: Any, *args: Any, **kwargs: Any
                ) -> Any:
                    start = time.time()
                    response = await original_async_create(self_inner, *args, **kwargs)
                    latency_ms = (time.time() - start) * 1000

                    try:
                        model = kwargs.get("model", "unknown")
                        usage = getattr(response, "usage", None)
                        if usage:
                            tracker.log_call(
                                model=model,
                                input_tokens=getattr(usage, "input_tokens", 0) or 0,
                                output_tokens=getattr(usage, "output_tokens", 0) or 0,
                                latency_ms=latency_ms,
                            )
                    except Exception:
                        pass

                    return response

                cls_async_messages.create = patched_async_create  # type: ignore[method-assign,assignment]
    except Exception:
        pass
