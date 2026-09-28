"""
Patches the Anthropic Python SDK to automatically intercept
``messages.create`` and ``messages.stream`` calls and log them to the tracker.

Supports sync and async clients, including streaming, and the beta Messages API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

from llmtrack.integrations._base import (
    Target,
    Usage,
    as_int,
    as_str,
    patch_target,
    resolve_attr,
)

if TYPE_CHECKING:
    from llmtrack.tracker import CostTracker


def message_usage_from(usage: Any, model: Optional[str] = None) -> Usage:
    """Anthropic's ``input_tokens`` excludes cache reads/writes; add them back."""
    fresh = as_int(getattr(usage, "input_tokens", 0))
    cache_read = as_int(getattr(usage, "cache_read_input_tokens", 0))
    cache_write = as_int(getattr(usage, "cache_creation_input_tokens", 0))
    return Usage(
        model=model,
        input_tokens=fresh + cache_read + cache_write,
        output_tokens=as_int(getattr(usage, "output_tokens", 0)),
        cached_input_tokens=cache_read,
        cache_creation_tokens=cache_write,
    )


def message_usage(message: Any) -> Optional[Usage]:
    usage = getattr(message, "usage", None)
    if not usage:
        return None
    return message_usage_from(usage, as_str(getattr(message, "model", None)))


class MessageStreamAccumulator:
    """
    Raw Messages events: ``message_start`` carries input usage, and each
    ``message_delta`` carries the cumulative output token count.
    """

    def __init__(self) -> None:
        self._usage: Optional[Usage] = None

    def feed(self, chunk: Any) -> None:
        kind = getattr(chunk, "type", None)
        if kind == "message_start":
            message = getattr(chunk, "message", None)
            self._usage = message_usage(message)
        elif kind == "message_delta" and self._usage is not None:
            usage = getattr(chunk, "usage", None)
            output = as_int(getattr(usage, "output_tokens", 0))
            if output:
                self._usage.output_tokens = output

    def usage(self) -> Optional[Usage]:
        return self._usage


def _targets() -> List[Target]:
    targets: List[Target] = []
    modules = ("anthropic.resources.messages", "anthropic.resources.beta.messages")
    for module in modules:
        for cls_name, is_async in (("Messages", False), ("AsyncMessages", True)):
            owner = resolve_attr(module, cls_name)
            if owner is None:
                continue
            targets.append(
                Target(
                    owner=owner,
                    attr="create",
                    extract=message_usage,
                    is_async=is_async,
                    make_accumulator=MessageStreamAccumulator,
                )
            )
            targets.append(
                Target(
                    owner=owner,
                    attr="stream",
                    extract=message_usage,
                    is_async=is_async,
                    kind="manager",
                )
            )
    return targets


def patch_anthropic(tracker: CostTracker) -> None:
    """
    Patch the Anthropic SDK to auto-track message completions.
    Called automatically when CostTracker(auto_patch=True).
    Safe to call repeatedly and for multiple trackers.
    """
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return

    for target in _targets():
        patch_target(tracker, target)
