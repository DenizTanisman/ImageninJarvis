import pytest

from core.base_strategy import CapabilityStrategy
from core.result import Error, Result, Success


class _DummyStrategy(CapabilityStrategy):
    name = "dummy"
    intent_keys = ("dummy", "echo")

    def can_handle(self, intent: dict) -> bool:
        return intent.get("type") == "dummy"

    async def execute(self, payload: dict) -> Result:
        if "fail" in payload:
            return Error(message="boom", user_message="hata oluştu")
        return Success(data=payload.get("text", ""))


def test_strategy_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        CapabilityStrategy()  # type: ignore[abstract]


def test_concrete_strategy_class_attrs() -> None:
    strategy = _DummyStrategy()
    assert strategy.name == "dummy"
    assert "echo" in strategy.intent_keys
    assert strategy.render_hint() == "text"


def test_can_handle_matches_intent_type() -> None:
    strategy = _DummyStrategy()
    assert strategy.can_handle({"type": "dummy"}) is True
    assert strategy.can_handle({"type": "other"}) is False


@pytest.mark.asyncio
async def test_execute_returns_success_for_valid_payload() -> None:
    strategy = _DummyStrategy()
    result = await strategy.execute({"text": "hello"})
    assert isinstance(result, Success)
    assert result.data == "hello"


@pytest.mark.asyncio
async def test_execute_returns_error_when_payload_signals_failure() -> None:
    strategy = _DummyStrategy()
    result = await strategy.execute({"fail": True})
    assert isinstance(result, Error)
    assert result.user_message == "hata oluştu"
