import pytest

from core.classifier import Classifier, Intent


@pytest.mark.asyncio
async def test_classifier_returns_intent_dataclass() -> None:
    classifier = Classifier()
    intent = await classifier.classify("merhaba")
    assert isinstance(intent, Intent)


@pytest.mark.asyncio
async def test_classifier_falls_back_for_any_input() -> None:
    classifier = Classifier()
    for sample in ["", "merhaba", "yarın 14'te toplantı ekle", "şunu çevir"]:
        intent = await classifier.classify(sample)
        assert intent.type == "fallback"
        assert intent.payload == {}


@pytest.mark.asyncio
async def test_classifier_preserves_text_after_strip() -> None:
    classifier = Classifier()
    intent = await classifier.classify("  Selam  ")
    assert intent.text == "Selam"


@pytest.mark.asyncio
async def test_intent_to_dict_round_trip() -> None:
    classifier = Classifier()
    intent = await classifier.classify("Merhaba dünya")
    snapshot = intent.to_dict()
    assert snapshot == {"type": "fallback", "text": "Merhaba dünya", "payload": {}}


def test_intent_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    intent = Intent(type="fallback", text="x", payload={})
    with pytest.raises(FrozenInstanceError):
        intent.type = "mail"  # type: ignore[misc]
