import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.classifier import Classifier, Intent
from services.gemini_client import GeminiClient, GeminiUnavailable

# ---------- legacy stub path (no Gemini wired) ----------


@pytest.mark.asyncio
async def test_classifier_returns_intent_dataclass() -> None:
    classifier = Classifier()
    intent = await classifier.classify("merhaba")
    assert isinstance(intent, Intent)


@pytest.mark.asyncio
async def test_classifier_falls_back_when_no_gemini_wired() -> None:
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


# ---------- Gemini-backed path ----------


def _gemini_returning_text(text: str) -> GeminiClient:
    model = AsyncMock()
    model.generate_content_async.return_value = SimpleNamespace(text=text)
    return GeminiClient(model=model, max_concurrent=2, max_attempts=1)


@pytest.mark.asyncio
async def test_classifier_detects_translation_intent() -> None:
    payload = {
        "type": "translation",
        "payload": {"text": "merhaba", "source": "auto", "target": "en"},
    }
    classifier = Classifier(_gemini_returning_text(json.dumps(payload)))
    intent = await classifier.classify("şunu İngilizceye çevir: merhaba")
    assert intent.type == "translation"
    assert intent.payload["text"] == "merhaba"
    assert intent.payload["target"] == "en"
    assert intent.payload["source"] == "auto"


@pytest.mark.asyncio
async def test_classifier_falls_back_when_translation_payload_invalid() -> None:
    """Model returned the right type but missed the required fields —
    we'd rather hand it to the general LLM than execute a malformed call."""
    raw = {"type": "translation", "payload": {"target": "en"}}  # text missing
    classifier = Classifier(_gemini_returning_text(json.dumps(raw)))
    intent = await classifier.classify("çeviri yap")
    assert intent.type == "fallback"


@pytest.mark.asyncio
async def test_classifier_falls_back_on_unknown_intent_type() -> None:
    raw = {"type": "send-tweet", "payload": {}}
    classifier = Classifier(_gemini_returning_text(json.dumps(raw)))
    intent = await classifier.classify("tweet at someone")
    assert intent.type == "fallback"


@pytest.mark.asyncio
async def test_classifier_falls_back_on_non_dict_response() -> None:
    classifier = Classifier(_gemini_returning_text(json.dumps(["not", "an", "object"])))
    intent = await classifier.classify("merhaba")
    assert intent.type == "fallback"


@pytest.mark.asyncio
async def test_classifier_falls_back_when_gemini_unreachable() -> None:
    async def boom(*_a, **_k):
        raise GeminiUnavailable("offline")

    model = AsyncMock()
    client = GeminiClient(model=model, max_concurrent=2, max_attempts=1)
    client.generate_json = boom  # type: ignore[method-assign]
    classifier = Classifier(client)
    intent = await classifier.classify("şunu çevir")
    assert intent.type == "fallback"


@pytest.mark.asyncio
async def test_classifier_falls_back_when_gemini_returns_non_json() -> None:
    classifier = Classifier(_gemini_returning_text("merhaba — burası json değil"))
    intent = await classifier.classify("şunu çevir")
    assert intent.type == "fallback"


@pytest.mark.asyncio
async def test_classifier_short_circuits_empty_input_without_calling_gemini() -> None:
    model = AsyncMock()
    client = GeminiClient(model=model, max_concurrent=2, max_attempts=1)
    classifier = Classifier(client)
    intent = await classifier.classify("   ")
    assert intent.type == "fallback"
    model.generate_content_async.assert_not_called()
