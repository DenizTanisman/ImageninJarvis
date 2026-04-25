from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from services.gemini_client import GeminiClient, GeminiUnavailable


def _make_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(text=text)


def _client_with_model(model: AsyncMock, *, max_attempts: int = 3) -> GeminiClient:
    return GeminiClient(model=model, max_attempts=max_attempts, max_concurrent=2)


def test_constructor_requires_api_key_or_model() -> None:
    with pytest.raises(ValueError):
        GeminiClient()


@pytest.mark.asyncio
async def test_generate_text_returns_text_on_success() -> None:
    model = AsyncMock()
    model.generate_content_async.return_value = _make_response("Merhaba")
    client = _client_with_model(model)
    out = await client.generate_text("Selam")
    assert out == "Merhaba"
    model.generate_content_async.assert_awaited_once_with("Selam")


@pytest.mark.asyncio
async def test_generate_text_passes_system_prompt() -> None:
    model = AsyncMock()
    model.generate_content_async.return_value = _make_response("ok")
    client = _client_with_model(model)
    await client.generate_text("user prompt", system="you are a helper")
    model.generate_content_async.assert_awaited_once_with(
        ["you are a helper", "user prompt"]
    )


@pytest.mark.asyncio
async def test_generate_text_retries_then_succeeds() -> None:
    model = AsyncMock()
    model.generate_content_async.side_effect = [
        RuntimeError("transient 1"),
        RuntimeError("transient 2"),
        _make_response("nihayet"),
    ]
    client = _client_with_model(model)
    out = await client.generate_text("Selam")
    assert out == "nihayet"
    assert model.generate_content_async.await_count == 3


@pytest.mark.asyncio
async def test_generate_text_raises_unavailable_after_max_attempts() -> None:
    model = AsyncMock()
    model.generate_content_async.side_effect = RuntimeError("boom")
    client = _client_with_model(model, max_attempts=3)
    with pytest.raises(GeminiUnavailable):
        await client.generate_text("Selam")
    assert model.generate_content_async.await_count == 3


@pytest.mark.asyncio
async def test_generate_json_parses_clean_json() -> None:
    model = AsyncMock()
    model.generate_content_async.return_value = _make_response('{"type": "fallback"}')
    client = _client_with_model(model)
    out = await client.generate_json("classify")
    assert out == {"type": "fallback"}


@pytest.mark.asyncio
async def test_generate_json_strips_code_fence() -> None:
    model = AsyncMock()
    model.generate_content_async.return_value = _make_response(
        '```json\n{"type": "translation"}\n```'
    )
    client = _client_with_model(model)
    out = await client.generate_json("classify")
    assert out == {"type": "translation"}


@pytest.mark.asyncio
async def test_generate_json_raises_on_invalid_response() -> None:
    model = AsyncMock()
    model.generate_content_async.return_value = _make_response("definitely not json")
    client = _client_with_model(model)
    with pytest.raises(ValueError):
        await client.generate_json("classify")


@pytest.mark.asyncio
async def test_semaphore_caps_concurrent_calls() -> None:
    """With max_concurrent=2 and 5 callers, never more than 2 in flight."""
    in_flight = 0
    max_seen = 0

    async def slow_call(*_args: object, **_kwargs: object) -> SimpleNamespace:
        nonlocal in_flight, max_seen
        in_flight += 1
        max_seen = max(max_seen, in_flight)
        import asyncio

        await asyncio.sleep(0.02)
        in_flight -= 1
        return _make_response("ok")

    model = AsyncMock()
    model.generate_content_async.side_effect = slow_call
    client = GeminiClient(model=model, max_concurrent=2, max_attempts=1)

    import asyncio

    await asyncio.gather(*(client.generate_text(f"p{i}") for i in range(5)))
    assert max_seen <= 2
