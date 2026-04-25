from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.base_strategy import CapabilityStrategy
from core.classifier import Classifier, Intent
from core.dispatcher import FALLBACK_SYSTEM_PROMPT, Dispatcher
from core.registry import CapabilityRegistry
from core.result import Error, Result, Success
from services.gemini_client import GeminiClient


def _gemini_with_text(text: str) -> GeminiClient:
    model = AsyncMock()
    model.generate_content_async.return_value = SimpleNamespace(text=text)
    return GeminiClient(model=model, max_concurrent=2, max_attempts=1)


def _gemini_that_fails() -> GeminiClient:
    model = AsyncMock()
    model.generate_content_async.side_effect = RuntimeError("offline")
    return GeminiClient(model=model, max_concurrent=2, max_attempts=1)


@pytest.mark.asyncio
async def test_handle_empty_input_returns_user_friendly_error() -> None:
    dispatcher = Dispatcher(
        classifier=Classifier(),
        registry=CapabilityRegistry(),
        gemini=_gemini_with_text("ignored"),
    )
    result = await dispatcher.handle("   ")
    assert isinstance(result, Error)
    assert result.log_level == "info"


@pytest.mark.asyncio
async def test_fallback_path_returns_success_with_gemini_response() -> None:
    gemini = _gemini_with_text("merhaba!")
    dispatcher = Dispatcher(
        classifier=Classifier(),
        registry=CapabilityRegistry(),
        gemini=gemini,
    )
    result = await dispatcher.handle("Selam")
    assert isinstance(result, Success)
    assert result.data == "merhaba!"
    assert result.meta == {"source": "fallback"}


@pytest.mark.asyncio
async def test_fallback_wraps_user_text_and_uses_system_prompt() -> None:
    captured: dict[str, object] = {}

    async def fake_generate(self, prompt: str, *, system: str | None = None) -> str:
        captured["prompt"] = prompt
        captured["system"] = system
        return "ok"

    gemini = _gemini_with_text("ignored")
    gemini.generate_text = fake_generate.__get__(gemini, GeminiClient)  # type: ignore[method-assign]

    dispatcher = Dispatcher(
        classifier=Classifier(),
        registry=CapabilityRegistry(),
        gemini=gemini,
    )
    await dispatcher.handle("Sevdiğim renk mavidir")

    assert captured["system"] == FALLBACK_SYSTEM_PROMPT
    assert isinstance(captured["prompt"], str)
    assert captured["prompt"].startswith("<user_content>")
    assert captured["prompt"].endswith("</user_content>")
    assert "Sevdiğim renk mavidir" in captured["prompt"]


@pytest.mark.asyncio
async def test_fallback_returns_error_when_gemini_unreachable() -> None:
    dispatcher = Dispatcher(
        classifier=Classifier(),
        registry=CapabilityRegistry(),
        gemini=_gemini_that_fails(),
    )
    result = await dispatcher.handle("merhaba")
    assert isinstance(result, Error)
    assert result.retry_after == 10


class _CapturingClassifier(Classifier):
    def __init__(self, intent_type: str) -> None:
        self._intent_type = intent_type

    async def classify(self, text: str) -> Intent:
        return Intent(type=self._intent_type, text=text.strip(), payload={"foo": "bar"})  # type: ignore[arg-type]


class _MailLikeStrategy(CapabilityStrategy):
    name = "mail"
    intent_keys = ("mail",)

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def can_handle(self, intent: dict) -> bool:
        return intent.get("type") == "mail"

    async def execute(self, payload: dict) -> Result:
        self.calls.append(payload)
        return Success(data="mail handled", ui_type="MailCard")


@pytest.mark.asyncio
async def test_routes_to_matching_strategy_when_intent_is_not_fallback() -> None:
    registry = CapabilityRegistry()
    strategy = _MailLikeStrategy()
    registry.register(strategy)

    dispatcher = Dispatcher(
        classifier=_CapturingClassifier("mail"),
        registry=registry,
        gemini=_gemini_with_text("should-not-be-called"),
    )
    result = await dispatcher.handle("bugün maillerimi özetle")
    assert isinstance(result, Success)
    assert result.ui_type == "MailCard"
    assert strategy.calls == [{"text": "bugün maillerimi özetle", "foo": "bar"}]


@pytest.mark.asyncio
async def test_falls_back_when_no_registered_strategy_handles_intent() -> None:
    registry = CapabilityRegistry()  # empty
    dispatcher = Dispatcher(
        classifier=_CapturingClassifier("mail"),
        registry=registry,
        gemini=_gemini_with_text("genel cevap"),
    )
    result = await dispatcher.handle("bugün maillerimi özetle")
    assert isinstance(result, Success)
    assert result.data == "genel cevap"
    assert result.meta == {"source": "fallback"}


@pytest.mark.asyncio
async def test_fallback_intent_skips_registry_lookup() -> None:
    registry = CapabilityRegistry()
    accidental = _MailLikeStrategy()
    registry.register(accidental)

    dispatcher = Dispatcher(
        classifier=Classifier(),  # always fallback
        registry=registry,
        gemini=_gemini_with_text("genel cevap"),
    )
    result = await dispatcher.handle("Selam")
    assert isinstance(result, Success)
    assert result.data == "genel cevap"
    assert accidental.calls == []
