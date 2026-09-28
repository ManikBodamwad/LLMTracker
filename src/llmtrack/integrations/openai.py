"""
Patches the OpenAI Python SDK to automatically intercept
chat completion, Responses API and embedding calls and log them to the tracker.

Supports sync and async clients, including streaming. Module-level helpers such
as ``openai.chat.completions.create`` resolve to the same patched methods, so
each call is recorded exactly once.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

from llmtrack.integrations._base import (
    ChatStreamAccumulator,
    Target,
    Usage,
    as_int,
    as_str,
    chat_usage,
    embeddings_usage,
    patch_target,
    resolve_attr,
)

if TYPE_CHECKING:
    from llmtrack.tracker import CostTracker


def responses_usage_from(usage: Any, model: Optional[str] = None) -> Usage:
    details = getattr(usage, "input_tokens_details", None)
    return Usage(
        model=model,
        input_tokens=as_int(getattr(usage, "input_tokens", 0)),
        output_tokens=as_int(getattr(usage, "output_tokens", 0)),
        cached_input_tokens=as_int(getattr(details, "cached_tokens", 0)),
    )


def responses_usage(response: Any) -> Optional[Usage]:
    usage = getattr(response, "usage", None)
    if not usage:
        return None
    return responses_usage_from(usage, as_str(getattr(response, "model", None)))


class ResponsesStreamAccumulator:
    """Responses API streams report usage on the terminal ``response.*`` event."""

    _TERMINAL = ("response.completed", "response.incomplete", "response.failed")

    def __init__(self) -> None:
        self._usage: Optional[Usage] = None

    def feed(self, chunk: Any) -> None:
        if getattr(chunk, "type", None) in self._TERMINAL:
            self._usage = responses_usage(getattr(chunk, "response", None))

    def usage(self) -> Optional[Usage]:
        return self._usage


def _targets() -> List[Target]:
    targets: List[Target] = []

    def add(
        module: str,
        sync_cls: str,
        async_cls: str,
        attr: str,
        extract: Any,
        accumulator: Any = None,
        inject: bool = False,
    ) -> None:
        for cls_name, is_async in ((sync_cls, False), (async_cls, True)):
            owner = resolve_attr(module, cls_name)
            if owner is not None:
                targets.append(
                    Target(
                        owner=owner,
                        attr=attr,
                        extract=extract,
                        is_async=is_async,
                        make_accumulator=accumulator,
                        inject_stream_usage=inject,
                    )
                )

    chat = "openai.resources.chat.completions"
    add(
        chat,
        "Completions",
        "AsyncCompletions",
        "create",
        chat_usage,
        ChatStreamAccumulator,
        inject=True,
    )
    add(chat, "Completions", "AsyncCompletions", "parse", chat_usage)

    responses = "openai.resources.responses"
    add(
        responses,
        "Responses",
        "AsyncResponses",
        "create",
        responses_usage,
        ResponsesStreamAccumulator,
    )
    add(responses, "Responses", "AsyncResponses", "parse", responses_usage)

    add(
        "openai.resources.embeddings",
        "Embeddings",
        "AsyncEmbeddings",
        "create",
        embeddings_usage,
    )
    return targets


def patch_openai(tracker: CostTracker) -> None:
    """
    Patch the OpenAI SDK to auto-track chat completions, Responses API calls and
    embeddings. Called automatically when CostTracker(auto_patch=True).
    Safe to call repeatedly and for multiple trackers.
    """
    try:
        import openai  # noqa: F401
    except ImportError:
        return

    for target in _targets():
        patch_target(tracker, target)
