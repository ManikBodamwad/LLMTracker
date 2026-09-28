"""
Shared machinery for the SDK integrations.

Each SDK method is wrapped at most once, no matter how many trackers ask for
it: the wrapper carries a weak set of registered trackers and logs each call to
all of them. Streaming responses are wrapped in a proxy that records usage when
the stream finishes.
"""

from __future__ import annotations

import functools
import importlib
import logging
import time
import weakref
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Protocol, Tuple

if TYPE_CHECKING:
    from llmtrack.tracker import CostTracker

logger = logging.getLogger("llmtrack")

_REGISTRY_ATTR = "__llmtrack_trackers__"

# (owner, attribute name, wrapper) for every patch installed by this process.
_INSTALLED: List[Tuple[Any, str, Any]] = []


@dataclass
class Usage:
    """Token usage extracted from an SDK response."""

    model: Optional[str] = None
    input_tokens: int = 0  # total prompt tokens, including cached
    output_tokens: int = 0
    cached_input_tokens: int = 0
    cache_creation_tokens: int = 0


class Accumulator(Protocol):
    """Collects usage from the chunks of a streaming response."""

    def feed(self, chunk: Any) -> None: ...

    def usage(self) -> Optional[Usage]: ...


Extractor = Callable[[Any], Optional[Usage]]


@dataclass(frozen=True)
class Target:
    """One SDK method to instrument."""

    owner: Any
    attr: str
    extract: Extractor
    is_async: bool = False
    # "call": returns the response (or a stream when stream=True).
    # "manager": returns a stream context manager (Anthropic ``messages.stream``).
    kind: str = "call"
    make_accumulator: Optional[Callable[[], Accumulator]] = None
    inject_stream_usage: bool = False
    positional_model: bool = False


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def as_int(value: Any) -> int:
    """Return ``value`` if it is a real integer, else 0 (None, mocks, ...)."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def as_str(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value else None


def resolve_attr(module_path: str, *names: str) -> Any:
    """Import ``module_path`` and walk ``names``; None if anything is missing."""
    try:
        obj: Any = importlib.import_module(module_path)
    except ImportError:
        return None
    for name in names:
        obj = getattr(obj, name, None)
        if obj is None:
            return None
    return obj


# --------------------------------------------------------------------------
# OpenAI-style usage (OpenAI chat / Responses / embeddings, LiteLLM)
# --------------------------------------------------------------------------


def chat_usage_from(usage: Any, model: Optional[str] = None) -> Usage:
    details = getattr(usage, "prompt_tokens_details", None)
    return Usage(
        model=model,
        input_tokens=as_int(getattr(usage, "prompt_tokens", 0)),
        output_tokens=as_int(getattr(usage, "completion_tokens", 0)),
        cached_input_tokens=as_int(getattr(details, "cached_tokens", 0)),
        cache_creation_tokens=as_int(getattr(usage, "cache_creation_input_tokens", 0)),
    )


def chat_usage(response: Any) -> Optional[Usage]:
    usage = getattr(response, "usage", None)
    if not usage:
        return None
    return chat_usage_from(usage, as_str(getattr(response, "model", None)))


def embeddings_usage(response: Any) -> Optional[Usage]:
    usage = getattr(response, "usage", None)
    if not usage:
        return None
    return Usage(
        model=as_str(getattr(response, "model", None)),
        input_tokens=as_int(getattr(usage, "prompt_tokens", 0)),
    )


class ChatStreamAccumulator:
    """OpenAI/LiteLLM chat chunks: usage arrives on the final chunk."""

    def __init__(self) -> None:
        self._usage: Any = None
        self._model: Optional[str] = None

    def feed(self, chunk: Any) -> None:
        usage = getattr(chunk, "usage", None)
        if usage:
            self._usage = usage
        model = as_str(getattr(chunk, "model", None))
        if model:
            self._model = model

    def usage(self) -> Optional[Usage]:
        if not self._usage:
            return None
        return chat_usage_from(self._usage, self._model)


# --------------------------------------------------------------------------
# Patching
# --------------------------------------------------------------------------


def patch_target(tracker: CostTracker, target: Target) -> None:
    """Instrument ``target`` for ``tracker``; idempotent across trackers."""
    current = getattr(target.owner, target.attr, None)
    if current is None:
        return

    registry = getattr(current, _REGISTRY_ATTR, None)
    if isinstance(registry, weakref.WeakSet):
        registry.add(tracker)
        return

    registry = weakref.WeakSet([tracker])
    wrapper = _build_wrapper(current, target, registry)
    setattr(wrapper, _REGISTRY_ATTR, registry)
    setattr(target.owner, target.attr, wrapper)
    _INSTALLED.append((target.owner, target.attr, wrapper))


def unregister_tracker(tracker: CostTracker) -> None:
    """Detach ``tracker`` from every installed wrapper."""
    for _, _, wrapper in _INSTALLED:
        registry = getattr(wrapper, _REGISTRY_ATTR, None)
        if isinstance(registry, weakref.WeakSet):
            registry.discard(tracker)


def restore_all() -> None:
    """Remove every patch installed by llmtrack, restoring the original methods."""
    while _INSTALLED:
        owner, attr, wrapper = _INSTALLED.pop()
        if getattr(owner, attr, None) is wrapper:
            setattr(owner, attr, getattr(wrapper, "__wrapped__"))


def _build_wrapper(original: Any, target: Target, registry: Any) -> Any:
    def prepare(args: Any, kwargs: Any) -> Tuple[List[Any], bool, str]:
        trackers = list(registry)
        streaming = bool(kwargs.get("stream")) and target.kind == "call"
        if (
            streaming
            and target.inject_stream_usage
            and any(getattr(t, "inject_stream_usage", True) for t in trackers)
        ):
            _inject_stream_usage(kwargs)
        return trackers, streaming, _model_from(target, args, kwargs)

    def emit(
        trackers: List[Any], model: str, usage: Optional[Usage], started: float
    ) -> None:
        if usage is None:
            logger.debug("llmtrack: no usage reported for %s call", model)
            return
        latency_ms = (time.perf_counter() - started) * 1000
        for tracker in trackers:
            try:
                tracker.log_call(
                    model=model if model != "unknown" else usage.model or model,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    latency_ms=latency_ms,
                    cached_input_tokens=usage.cached_input_tokens,
                    cache_creation_tokens=usage.cache_creation_tokens,
                )
            except Exception:
                logger.warning("llmtrack failed to record a call", exc_info=True)

    def finish(
        response: Any,
        trackers: List[Any],
        streaming: bool,
        model: str,
        started: float,
    ) -> Any:
        try:
            if target.kind == "manager":
                if target.is_async:
                    return AsyncManagerProxy(
                        response,
                        lambda u: emit(trackers, model, u, started),
                        target.extract,
                    )
                return SyncManagerProxy(
                    response,
                    lambda u: emit(trackers, model, u, started),
                    target.extract,
                )
            if streaming and target.make_accumulator is not None:
                proxy_cls = AsyncStreamProxy if target.is_async else SyncStreamProxy
                return proxy_cls(
                    response,
                    target.make_accumulator(),
                    lambda u: emit(trackers, model, u, started),
                )
            emit(trackers, model, target.extract(response), started)
        except Exception:
            logger.warning("llmtrack failed to record a call", exc_info=True)
        return response

    if target.kind == "manager":
        # ``stream()`` returns a context manager synchronously for both the
        # sync and async clients.
        @functools.wraps(original, updated=())
        def manager_wrapper(*args: Any, **kwargs: Any) -> Any:
            trackers, streaming, model = prepare(args, kwargs)
            if not trackers:
                return original(*args, **kwargs)
            started = time.perf_counter()
            return finish(
                original(*args, **kwargs), trackers, streaming, model, started
            )

        return manager_wrapper

    if target.is_async:

        @functools.wraps(original, updated=())
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            trackers, streaming, model = prepare(args, kwargs)
            if not trackers:
                return await original(*args, **kwargs)
            started = time.perf_counter()
            response = await original(*args, **kwargs)
            return finish(response, trackers, streaming, model, started)

        return async_wrapper

    @functools.wraps(original, updated=())
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        trackers, streaming, model = prepare(args, kwargs)
        if not trackers:
            return original(*args, **kwargs)
        started = time.perf_counter()
        response = original(*args, **kwargs)
        return finish(response, trackers, streaming, model, started)

    return sync_wrapper


def _model_from(target: Target, args: Any, kwargs: Any) -> str:
    model = kwargs.get("model")
    if model is None and target.positional_model and args:
        model = args[0]
    return model if isinstance(model, str) and model else "unknown"


def _inject_stream_usage(kwargs: Any) -> None:
    """Ask the API to report usage on the final streamed chunk."""
    options = kwargs.get("stream_options")
    if options is None:
        kwargs["stream_options"] = {"include_usage": True}
    elif isinstance(options, dict) and "include_usage" not in options:
        kwargs["stream_options"] = {**options, "include_usage": True}


# --------------------------------------------------------------------------
# Stream proxies
# --------------------------------------------------------------------------


class _Finishable:
    """Reports usage exactly once when the wrapped stream is done."""

    _finished = False

    def _report(self, usage_getter: Callable[[], Optional[Usage]]) -> None:
        if self._finished:
            return
        self._finished = True
        try:
            self._on_done(usage_getter())  # type: ignore[attr-defined]
        except Exception:
            logger.warning("llmtrack failed to record a streamed call", exc_info=True)


class _StreamProxy(_Finishable):
    def __init__(
        self,
        stream: Any,
        accumulator: Accumulator,
        on_done: Callable[[Optional[Usage]], None],
    ) -> None:
        self._stream = stream
        self._accumulator = accumulator
        self._on_done = on_done

    def __getattr__(self, name: str) -> Any:
        if name in ("_stream", "_accumulator", "_on_done"):
            raise AttributeError(name)
        return getattr(self._stream, name)

    def _feed(self, chunk: Any) -> None:
        try:
            self._accumulator.feed(chunk)
        except Exception:
            logger.debug("llmtrack could not read a stream chunk", exc_info=True)

    def _finish(self) -> None:
        self._report(self._accumulator.usage)


class SyncStreamProxy(_StreamProxy):
    """Transparent wrapper around a sync SDK stream."""

    def __init__(self, stream: Any, *args: Any, **kwargs: Any) -> None:
        super().__init__(stream, *args, **kwargs)
        self._iterator = iter(stream)

    def __iter__(self) -> SyncStreamProxy:
        return self

    def __next__(self) -> Any:
        try:
            chunk = next(self._iterator)
        except BaseException:
            self._finish()
            raise
        self._feed(chunk)
        return chunk

    def __enter__(self) -> SyncStreamProxy:
        self._stream.__enter__()
        return self

    def __exit__(self, *exc_info: Any) -> Any:
        try:
            return self._stream.__exit__(*exc_info)
        finally:
            self._finish()

    def close(self) -> Any:
        try:
            return self._stream.close()
        finally:
            self._finish()


class AsyncStreamProxy(_StreamProxy):
    """Transparent wrapper around an async SDK stream."""

    def __init__(self, stream: Any, *args: Any, **kwargs: Any) -> None:
        super().__init__(stream, *args, **kwargs)
        self._iterator = stream.__aiter__()

    def __aiter__(self) -> AsyncStreamProxy:
        return self

    async def __anext__(self) -> Any:
        try:
            chunk = await self._iterator.__anext__()
        except BaseException:
            self._finish()
            raise
        self._feed(chunk)
        return chunk

    async def __aenter__(self) -> AsyncStreamProxy:
        await self._stream.__aenter__()
        return self

    async def __aexit__(self, *exc_info: Any) -> Any:
        try:
            return await self._stream.__aexit__(*exc_info)
        finally:
            self._finish()

    async def close(self) -> Any:
        try:
            return await self._stream.close()
        finally:
            self._finish()


class _ManagerProxy(_Finishable):
    """
    Wraps Anthropic's ``messages.stream()`` context manager. Usage is read from
    the stream's accumulated message snapshot when the block exits.
    """

    def __init__(
        self,
        manager: Any,
        on_done: Callable[[Optional[Usage]], None],
        extract: Extractor,
    ) -> None:
        self._manager = manager
        self._on_done = on_done
        self._extract = extract
        self._stream: Any = None

    def __getattr__(self, name: str) -> Any:
        if name in ("_manager", "_on_done", "_extract", "_stream"):
            raise AttributeError(name)
        return getattr(self._manager, name)

    def _snapshot_usage(self) -> Optional[Usage]:
        if self._stream is None:
            return None
        try:
            snapshot = self._stream.current_message_snapshot
        except (AssertionError, AttributeError):
            return None  # the stream ended before any event arrived
        return self._extract(snapshot)


class SyncManagerProxy(_ManagerProxy):
    def __enter__(self) -> Any:
        self._stream = self._manager.__enter__()
        return self._stream

    def __exit__(self, *exc_info: Any) -> Any:
        try:
            return self._manager.__exit__(*exc_info)
        finally:
            self._report(self._snapshot_usage)


class AsyncManagerProxy(_ManagerProxy):
    async def __aenter__(self) -> Any:
        self._stream = await self._manager.__aenter__()
        return self._stream

    async def __aexit__(self, *exc_info: Any) -> Any:
        try:
            return await self._manager.__aexit__(*exc_info)
        finally:
            self._report(self._snapshot_usage)
