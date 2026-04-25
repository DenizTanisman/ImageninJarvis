"""Targeted tests for the retry-policy carve-outs (request-side errors)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from google.api_core import exceptions as gax

from services.gemini_client import GeminiClient, GeminiUnavailable


def _client(model: AsyncMock) -> GeminiClient:
    return GeminiClient(model=model, max_concurrent=2, max_attempts=3)


@pytest.mark.asyncio
async def test_quota_error_does_not_retry() -> None:
    model = AsyncMock()
    model.generate_content_async.side_effect = gax.ResourceExhausted("429 quota")
    client = _client(model)
    with pytest.raises(GeminiUnavailable) as exc_info:
        await client.generate_text("hi")
    assert "ResourceExhausted" in str(exc_info.value)
    assert model.generate_content_async.await_count == 1


@pytest.mark.asyncio
async def test_permission_denied_does_not_retry() -> None:
    model = AsyncMock()
    model.generate_content_async.side_effect = gax.PermissionDenied("403 denied")
    client = _client(model)
    with pytest.raises(GeminiUnavailable):
        await client.generate_text("hi")
    assert model.generate_content_async.await_count == 1


@pytest.mark.asyncio
async def test_invalid_argument_does_not_retry() -> None:
    model = AsyncMock()
    model.generate_content_async.side_effect = gax.InvalidArgument("400 bad")
    client = _client(model)
    with pytest.raises(GeminiUnavailable):
        await client.generate_text("hi")
    assert model.generate_content_async.await_count == 1


@pytest.mark.asyncio
async def test_transient_runtime_error_still_retries() -> None:
    model = AsyncMock()
    model.generate_content_async.side_effect = [
        RuntimeError("flaky 1"),
        RuntimeError("flaky 2"),
        SimpleNamespace(text="ok"),
    ]
    client = _client(model)
    out = await client.generate_text("hi")
    assert out == "ok"
    assert model.generate_content_async.await_count == 3
