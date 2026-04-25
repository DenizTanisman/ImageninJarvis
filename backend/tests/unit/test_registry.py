import pytest

from core.base_strategy import CapabilityStrategy
from core.registry import CapabilityRegistry
from core.result import Result, Success


class _Strategy(CapabilityStrategy):
    def __init__(self, name: str, accepts: str) -> None:
        self.name = name
        self.intent_keys = (accepts,)
        self._accepts = accepts

    def can_handle(self, intent: dict) -> bool:
        return intent.get("type") == self._accepts

    async def execute(self, payload: dict) -> Result:
        return Success(data=payload)


def test_register_and_find_returns_matching_strategy() -> None:
    registry = CapabilityRegistry()
    mail = _Strategy("mail", "mail")
    translation = _Strategy("translation", "translation")
    registry.register(mail)
    registry.register(translation)

    assert registry.find({"type": "mail"}) is mail
    assert registry.find({"type": "translation"}) is translation


def test_find_returns_none_when_no_strategy_handles_intent() -> None:
    registry = CapabilityRegistry()
    registry.register(_Strategy("mail", "mail"))
    assert registry.find({"type": "calendar"}) is None
    assert registry.find({"type": "fallback"}) is None


def test_register_rejects_duplicate_names() -> None:
    registry = CapabilityRegistry()
    registry.register(_Strategy("mail", "mail"))
    with pytest.raises(ValueError):
        registry.register(_Strategy("mail", "mail-dup"))


def test_all_returns_a_copy() -> None:
    registry = CapabilityRegistry()
    s1 = _Strategy("mail", "mail")
    registry.register(s1)
    snapshot = registry.all()
    assert snapshot == [s1]
    snapshot.clear()
    assert registry.all() == [s1]


def test_clear_empties_the_registry() -> None:
    registry = CapabilityRegistry()
    registry.register(_Strategy("mail", "mail"))
    registry.clear()
    assert registry.all() == []
