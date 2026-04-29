"""Tests for JournalReportStrategy.

httpx is short-circuited via httpx.MockTransport so no network ever fires.
We exercise tag detection (whitelist + /date{...}), the "son N gün" range
sniffer, every error path the Reporter can hand back, and the success path.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import httpx
import pytest

from capabilities.journal.strategy import JournalReportStrategy
from core.result import Error, Success


def _strategy_with_handler(handler) -> tuple[JournalReportStrategy, list[httpx.Request]]:
    """Build a strategy whose async client is backed by `handler`.

    `handler` receives the httpx.Request and returns an httpx.Response.
    """
    captured: list[httpx.Request] = []

    def wrapper(req: httpx.Request) -> httpx.Response:
        captured.append(req)
        return handler(req)

    transport = httpx.MockTransport(wrapper)

    def factory():
        return httpx.AsyncClient(transport=transport, timeout=5.0)

    strategy = JournalReportStrategy(
        reporter_url="http://reporter.local",
        reporter_key="bridge-secret",
        client_factory=factory,
    )
    return strategy, captured


# ---------------------------------------------------------------------------
# can_handle / tag detection
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text",
    ["/detail", "/todo son 7 gün", "/concern", "/success", "/date{15.04.2026}"],
)
def test_can_handle_tag_in_text(text):
    strategy = JournalReportStrategy("http://x", "y")
    assert strategy.can_handle({"text": text})


def test_can_handle_journal_intent_type():
    strategy = JournalReportStrategy("http://x", "y")
    assert strategy.can_handle({"type": "journal", "text": "anything"})


@pytest.mark.parametrize("text", ["", "merhaba", "/foo", "/detailed", "detail"])
def test_can_handle_rejects_non_tags(text):
    strategy = JournalReportStrategy("http://x", "y")
    assert not strategy.can_handle({"text": text})


# ---------------------------------------------------------------------------
# execute — success path
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_execute_returns_success_and_passes_tag_and_range():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "tag": "/todo",
                "raw_markdown": "# /todo Raporu\n- yapacak iş",
                "entry_count": 2,
                "date_range": {"start": "2026-04-23", "end": "2026-04-29"},
            },
        )

    strategy, captured = _strategy_with_handler(handler)
    result = await strategy.execute({"text": "/todo son 7 gün"})
    assert isinstance(result, Success)
    assert result.ui_type == "JournalReportCard"
    assert result.data["tag"] == "/todo"
    assert "yapacak iş" in result.data["markdown"]
    assert result.data["entry_count"] == 2

    sent = captured[0]
    body = json.loads(sent.content)
    assert body["tag"] == "/todo"
    assert body["date_range"]["start"] != body["date_range"]["end"]  # 7 day window
    assert sent.headers["authorization"] == "Bearer bridge-secret"


@pytest.mark.asyncio
async def test_execute_date_tag_omits_range():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"tag": "/date{15.04.2026}", "raw_markdown": "# Gün Raporu", "entry_count": 1},
        )

    strategy, captured = _strategy_with_handler(handler)
    result = await strategy.execute({"text": "/date{15.04.2026}"})
    assert isinstance(result, Success)
    body = json.loads(captured[0].content)
    assert body["tag"] == "/date{15.04.2026}"
    assert "date_range" not in body  # date tag carries its own date


@pytest.mark.asyncio
async def test_execute_no_tag_returns_error():
    strategy = JournalReportStrategy("http://x", "y")
    result = await strategy.execute({"text": "merhaba"})
    assert isinstance(result, Error)
    assert "anlamadım" in result.user_message


@pytest.mark.asyncio
async def test_execute_unconfigured_returns_error():
    strategy = JournalReportStrategy("", "")
    result = await strategy.execute({"text": "/detail"})
    assert isinstance(result, Error)
    assert "yapılandırılmamış" in result.user_message


# ---------------------------------------------------------------------------
# execute — Reporter error mapping
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,upstream_code,expected_substring",
    [
        (401, None, "kimlik"),
        (404, "no_entries", "günlük girişi"),
        (404, "date_not_in_range", "aralıkta giriş yok"),
        (429, None, "hızlı"),
        (502, None, "erişilemiyor"),
        (503, None, "erişilemiyor"),
        (500, None, "beklenmedik"),
    ],
)
async def test_execute_maps_reporter_errors(status, upstream_code, expected_substring):
    body = {"code": upstream_code, "message": "x"} if upstream_code else {"code": "x"}

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)

    strategy, _ = _strategy_with_handler(handler)
    result = await strategy.execute({"text": "/detail"})
    assert isinstance(result, Error)
    assert expected_substring in result.user_message.lower() or expected_substring in result.user_message


@pytest.mark.asyncio
async def test_execute_timeout_returns_retryable_error():
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow")

    strategy, _ = _strategy_with_handler(handler)
    result = await strategy.execute({"text": "/detail"})
    assert isinstance(result, Error)
    assert result.retry_after == 15


@pytest.mark.asyncio
async def test_execute_connect_error_returns_retryable_error():
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    strategy, _ = _strategy_with_handler(handler)
    result = await strategy.execute({"text": "/detail"})
    assert isinstance(result, Error)
    assert "ulaşamıyorum" in result.user_message
