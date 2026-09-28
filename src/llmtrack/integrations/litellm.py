"""
Patches the LiteLLM library to automatically intercept
completion and embedding calls (sync, async and streaming) and log them to the tracker.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from llmtrack.integrations._base import (
    ChatStreamAccumulator,
    Target,
    chat_usage,
    embeddings_usage,
    patch_target,
)

if TYPE_CHECKING:
    from llmtrack.tracker import CostTracker


def patch_litellm(tracker: CostTracker) -> None:
    """
    Patch LiteLLM to track calls.
    Safe to call repeatedly and for multiple trackers.
    """
    try:
        import litellm
    except ImportError:
        return

    targets: List[Target] = [
        Target(
            litellm,
            "completion",
            chat_usage,
            False,
            make_accumulator=ChatStreamAccumulator,
            inject_stream_usage=True,
            positional_model=True,
        ),
        Target(
            litellm,
            "acompletion",
            chat_usage,
            True,
            make_accumulator=ChatStreamAccumulator,
            inject_stream_usage=True,
            positional_model=True,
        ),
        Target(litellm, "embedding", embeddings_usage, False, positional_model=True),
        Target(litellm, "aembedding", embeddings_usage, True, positional_model=True),
    ]
    for target in targets:
        patch_target(tracker, target)
