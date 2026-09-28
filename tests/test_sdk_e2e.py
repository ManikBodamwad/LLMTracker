"""
End-to-end integration tests: real OpenAI / Anthropic clients talking to a mocked
HTTP transport, so the patched SDK methods run their real code paths.
"""

import json

import anthropic
import httpx
import openai
import pytest

try:  # newer anthropic releases are built on httpx2 instead of httpx
    import httpx2 as anthropic_httpx
except ImportError:  # pragma: no cover
    anthropic_httpx = httpx

from llmtrack import CostTracker
from llmtrack.integrations import _base
from llmtrack.integrations.anthropic import patch_anthropic
from llmtrack.integrations.openai import patch_openai
from llmtrack.storage.memory import MemoryStorage


@pytest.fixture
def tracker():
    """Tracker with SDK patches that are removed again after the test."""
    t = CostTracker(storage=MemoryStorage(), auto_patch=False)
    patch_openai(t)
    patch_anthropic(t)
    yield t
    _base.restore_all()


def _sse(*events):
    body = ""
    for name, data in events:
        prefix = f"event: {name}\n" if name else ""
        body += f"{prefix}data: {json.dumps(data)}\n\n"
    return body


def _handler(requests, responder):
    def handle(request):
        requests.append(json.loads(request.content or b"{}"))
        return responder(request)

    return handle


CHAT_JSON = {
    "id": "c1",
    "object": "chat.completion",
    "created": 1,
    "model": "gpt-4o-2024-08-06",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "hi"},
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 1000,
        "completion_tokens": 100,
        "total_tokens": 1100,
        "prompt_tokens_details": {"cached_tokens": 400},
    },
}


def _chat_chunks():
    base = {
        "id": "c1",
        "object": "chat.completion.chunk",
        "created": 1,
        "model": "gpt-4o",
    }
    yield {**base, "choices": [{"index": 0, "delta": {"content": "hi"}}]}
    yield {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
    yield {
        **base,
        "choices": [],
        "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
    }


def _openai_client(responder, requests, cls=openai.OpenAI, http_cls=httpx.Client):
    transport = httpx.MockTransport(_handler(requests, responder))
    return cls(api_key="k", http_client=http_cls(transport=transport))


def _json_response(payload):
    return lambda request: httpx.Response(200, json=payload)


def test_openai_call_recorded_once_with_cache_pricing(tracker):
    requests = []
    client = _openai_client(_json_response(CHAT_JSON), requests)

    with tracker.feature("chat"):
        client.chat.completions.create(model="gpt-4o", messages=[])

    (event,) = tracker.storage.query(days=1)
    assert event.feature == "chat"
    assert event.model == "gpt-4o"
    assert (event.input_tokens, event.output_tokens) == (1000, 100)
    assert event.cached_input_tokens == 400
    # 600 * $2.50 + 400 * $1.25 + 100 * $10 per 1M
    assert event.cost_usd == pytest.approx((1500 + 500 + 1000) / 1e6)


def test_module_level_openai_call_not_double_counted(tracker, monkeypatch):
    requests = []
    client = _openai_client(_json_response(CHAT_JSON), requests)
    monkeypatch.setattr(openai, "api_key", "k")
    # The module-level helper resolves to a default client; point that at ours.
    monkeypatch.setattr(openai, "_client", client)

    openai.chat.completions.create(model="gpt-4o", messages=[])

    assert len(tracker.storage.query(days=1)) == 1


def test_patching_is_idempotent_and_multi_tracker(tracker):
    second = CostTracker(storage=MemoryStorage(), auto_patch=False)
    patch_openai(tracker)
    patch_openai(second)
    patch_openai(second)

    client = _openai_client(_json_response(CHAT_JSON), [])
    client.chat.completions.create(model="gpt-4o", messages=[])

    assert len(tracker.storage.query(days=1)) == 1
    assert len(second.storage.query(days=1)) == 1

    second.unpatch()
    client.chat.completions.create(model="gpt-4o", messages=[])
    assert len(tracker.storage.query(days=1)) == 2
    assert len(second.storage.query(days=1)) == 1


def test_openai_stream_records_usage_and_injects_option(tracker):
    requests = []

    def responder(request):
        events = [(None, c) for c in _chat_chunks()] + [(None, "[DONE]")]
        body = "".join(f"data: {json.dumps(d)}\n\n" for _, d in events[:-1])
        body += "data: [DONE]\n\n"
        return httpx.Response(
            200, headers={"content-type": "text/event-stream"}, content=body
        )

    client = _openai_client(responder, requests)
    with tracker.feature("streamed"):
        stream = client.chat.completions.create(
            model="gpt-4o", messages=[], stream=True
        )
        chunks = list(stream)

    assert len(chunks) == 3
    assert requests[0]["stream_options"] == {"include_usage": True}
    (event,) = tracker.storage.query(days=1)
    assert event.feature == "streamed"
    assert (event.input_tokens, event.output_tokens) == (50, 20)


def test_openai_stream_context_manager_logs_once(tracker):
    def responder(request):
        body = "".join(f"data: {json.dumps(c)}\n\n" for c in _chat_chunks())
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=body + "data: [DONE]\n\n",
        )

    client = _openai_client(responder, [])
    with client.chat.completions.create(model="gpt-4o", messages=[], stream=True) as s:
        for _ in s:
            pass
    assert len(tracker.storage.query(days=1)) == 1


def test_stream_usage_injection_can_be_disabled():
    t = CostTracker(
        storage=MemoryStorage(), auto_patch=False, inject_stream_usage=False
    )
    patch_openai(t)
    try:
        requests = []

        def responder(request):
            body = "".join(f"data: {json.dumps(c)}\n\n" for c in _chat_chunks())
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=body + "data: [DONE]\n\n",
            )

        client = _openai_client(responder, requests)
        list(client.chat.completions.create(model="gpt-4o", messages=[], stream=True))
        assert "stream_options" not in requests[0]
    finally:
        _base.restore_all()


async def test_openai_async_and_async_stream(tracker):
    requests = []

    def responder(request):
        if json.loads(request.content).get("stream"):
            body = "".join(f"data: {json.dumps(c)}\n\n" for c in _chat_chunks())
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=body + "data: [DONE]\n\n",
            )
        return httpx.Response(200, json=CHAT_JSON)

    client = _openai_client(responder, requests, openai.AsyncOpenAI, httpx.AsyncClient)
    await client.chat.completions.create(model="gpt-4o", messages=[])
    stream = await client.chat.completions.create(
        model="gpt-4o", messages=[], stream=True
    )
    async for _ in stream:
        pass

    events = sorted(tracker.storage.query(days=1), key=lambda e: e.input_tokens)
    assert [e.input_tokens for e in events] == [50, 1000]


def test_openai_embeddings_and_responses(tracker):
    def responder(request):
        if request.url.path.endswith("/embeddings"):
            return httpx.Response(
                200,
                json={
                    "object": "list",
                    "model": "text-embedding-3-small",
                    "data": [{"object": "embedding", "index": 0, "embedding": [0.1]}],
                    "usage": {"prompt_tokens": 12, "total_tokens": 12},
                },
            )
        return httpx.Response(
            200,
            json={
                "id": "r1",
                "object": "response",
                "created_at": 1,
                "status": "completed",
                "model": "gpt-4o",
                "output": [],
                "parallel_tool_calls": True,
                "tool_choice": "auto",
                "tools": [],
                "usage": {
                    "input_tokens": 30,
                    "output_tokens": 10,
                    "total_tokens": 40,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens_details": {"reasoning_tokens": 0},
                },
            },
        )

    client = _openai_client(responder, [])
    client.embeddings.create(model="text-embedding-3-small", input="hi")
    client.responses.create(model="gpt-4o", input="hi")

    by_model = {e.model: e for e in tracker.storage.query(days=1)}
    assert by_model["text-embedding-3-small"].input_tokens == 12
    assert by_model["gpt-4o"].output_tokens == 10


MESSAGE_JSON = {
    "id": "m1",
    "type": "message",
    "role": "assistant",
    "model": "claude-sonnet-4-5",
    "content": [{"type": "text", "text": "hi"}],
    "stop_reason": "end_turn",
    "stop_sequence": None,
    "usage": {
        "input_tokens": 100,
        "output_tokens": 50,
        "cache_read_input_tokens": 1000,
        "cache_creation_input_tokens": 200,
    },
}


def _message_events():
    start = {**MESSAGE_JSON, "content": [], "stop_reason": None}
    start["usage"] = {**MESSAGE_JSON["usage"], "output_tokens": 1}
    return [
        ("message_start", {"type": "message_start", "message": start}),
        (
            "content_block_start",
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
        ),
        (
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "hi"},
            },
        ),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        (
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                "usage": {"output_tokens": 50},
            },
        ),
        ("message_stop", {"type": "message_stop"}),
    ]


def _anthropic_client(responder, cls=anthropic.Anthropic, is_async=False):
    transport = anthropic_httpx.MockTransport(_handler([], responder))
    http_cls = anthropic_httpx.AsyncClient if is_async else anthropic_httpx.Client
    return cls(api_key="k", http_client=http_cls(transport=transport))


def _anthropic_responder(request):
    if json.loads(request.content).get("stream"):
        return anthropic_httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=_sse(*_message_events()),
        )
    return anthropic_httpx.Response(200, json=MESSAGE_JSON)


CLAUDE_KW = dict(
    model="claude-sonnet-4-5",
    max_tokens=10,
    messages=[{"role": "user", "content": "hi"}],
)


def _check_claude_event(event):
    assert event.input_tokens == 1300  # 100 fresh + 1000 read + 200 written
    assert event.cached_input_tokens == 1000
    assert event.cache_creation_tokens == 200
    assert event.output_tokens == 50
    # 100 * $3 + 1000 * $0.30 + 200 * $3.75 + 50 * $15 per 1M
    assert event.cost_usd == pytest.approx((300 + 300 + 750 + 750) / 1e6)


def test_anthropic_create_with_cache_tokens(tracker):
    _anthropic_client(_anthropic_responder).messages.create(**CLAUDE_KW)
    (event,) = tracker.storage.query(days=1)
    _check_claude_event(event)


def test_anthropic_create_stream(tracker):
    client = _anthropic_client(_anthropic_responder)
    for _ in client.messages.create(**CLAUDE_KW, stream=True):
        pass
    (event,) = tracker.storage.query(days=1)
    _check_claude_event(event)


def test_anthropic_stream_helper(tracker):
    client = _anthropic_client(_anthropic_responder)
    with tracker.feature("claude_stream"):
        with client.messages.stream(**CLAUDE_KW) as stream:
            for _ in stream:
                pass
    (event,) = tracker.storage.query(days=1)
    assert event.feature == "claude_stream"
    _check_claude_event(event)


async def test_anthropic_async_paths(tracker):
    client = _anthropic_client(_anthropic_responder, anthropic.AsyncAnthropic, True)
    await client.messages.create(**CLAUDE_KW)
    async with client.messages.stream(**CLAUDE_KW) as stream:
        async for _ in stream:
            pass
    events = tracker.storage.query(days=1)
    assert len(events) == 2
    for event in events:
        _check_claude_event(event)
