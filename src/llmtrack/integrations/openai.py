"""
Patches the OpenAI Python SDK to automatically intercept
all chat completion calls and log them to the tracker.

Supports both sync and async clients.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from llmtrack.tracker import CostTracker


def patch_openai(tracker: CostTracker) -> None:
    """
    Patch the OpenAI SDK to auto-track all chat completions.
    Called automatically when CostTracker(auto_patch=True).
    """
    try:
        import openai
    except ImportError:
        return

    # Patch instance/class method on Completions if available
    try:
        if hasattr(openai, "resources") and hasattr(openai.resources, "chat"):
            chat_mod = openai.resources.chat
            if hasattr(chat_mod, "completions") and hasattr(
                chat_mod.completions, "Completions"
            ):
                cls_completions = chat_mod.completions.Completions
                original_sync_create = cls_completions.create

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
                                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                                output_tokens=getattr(usage, "completion_tokens", 0)
                                or 0,
                                latency_ms=latency_ms,
                            )
                    except Exception:
                        pass

                    return response

                cls_completions.create = patched_sync_create

            if hasattr(chat_mod, "completions") and hasattr(
                chat_mod.completions, "AsyncCompletions"
            ):
                cls_async_completions = chat_mod.completions.AsyncCompletions
                original_async_create = cls_async_completions.create

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
                                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                                output_tokens=getattr(usage, "completion_tokens", 0)
                                or 0,
                                latency_ms=latency_ms,
                            )
                    except Exception:
                        pass

                    return response

                cls_async_completions.create = patched_async_create
    except Exception:
        pass

    # Direct top-level module patching for compatibility
    try:
        if hasattr(openai, "chat") and hasattr(openai.chat, "completions"):
            original_create = openai.chat.completions.create

            def patched_create(*args: Any, **kwargs: Any) -> Any:
                start = time.time()
                response = original_create(*args, **kwargs)
                latency_ms = (time.time() - start) * 1000

                try:
                    model = kwargs.get("model", "unknown")
                    usage = getattr(response, "usage", None)
                    if usage:
                        tracker.log_call(
                            model=model,
                            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
                            latency_ms=latency_ms,
                        )
                except Exception:
                    pass

                return response

            openai.chat.completions.create = patched_create
    except Exception:
        pass
