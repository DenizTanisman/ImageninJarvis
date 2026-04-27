import json
from datetime import UTC
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


# ---------- calendar ----------


@pytest.mark.asyncio
async def test_classifier_detects_calendar_list_intent() -> None:
    raw = {"type": "calendar", "payload": {"action": "list", "days": 7}}
    classifier = Classifier(_gemini_returning_text(json.dumps(raw)))
    intent = await classifier.classify("bu haftaki etkinliklerim")
    assert intent.type == "calendar"
    assert intent.payload["action"] == "list"
    assert intent.payload["days"] == 7


@pytest.mark.asyncio
async def test_classifier_detects_calendar_create_intent() -> None:
    raw = {
        "type": "calendar",
        "payload": {
            "action": "create",
            "summary": "Sunum",
            "start": "2026-04-28T14:00:00+03:00",
            "end": "2026-04-28T15:00:00+03:00",
            "description": "",
        },
    }
    classifier = Classifier(_gemini_returning_text(json.dumps(raw)))
    intent = await classifier.classify("yarın 14'te 1 saatlik sunum ekle")
    assert intent.type == "calendar"
    assert intent.payload["action"] == "create"
    assert intent.payload["summary"] == "Sunum"


@pytest.mark.asyncio
async def test_classifier_falls_back_when_calendar_create_missing_fields() -> None:
    raw = {"type": "calendar", "payload": {"action": "create", "summary": "x"}}
    classifier = Classifier(_gemini_returning_text(json.dumps(raw)))
    intent = await classifier.classify("toplantı ekle")
    assert intent.type == "fallback"


@pytest.mark.asyncio
async def test_classifier_falls_back_on_unsupported_calendar_action() -> None:
    raw = {"type": "calendar", "payload": {"action": "delete", "event_id": "e1"}}
    classifier = Classifier(_gemini_returning_text(json.dumps(raw)))
    intent = await classifier.classify("toplantıyı sil")
    assert intent.type == "fallback"


# ---------- mail ----------


@pytest.mark.asyncio
async def test_classifier_detects_mail_daily_intent() -> None:
    raw = {"type": "mail", "payload": {"range_kind": "daily"}}
    classifier = Classifier(_gemini_returning_text(json.dumps(raw)))
    intent = await classifier.classify("bugünün maillerini özetle")
    assert intent.type == "mail"
    assert intent.payload["range_kind"] == "daily"


@pytest.mark.asyncio
async def test_classifier_detects_mail_weekly_intent() -> None:
    raw = {"type": "mail", "payload": {"range_kind": "weekly"}}
    classifier = Classifier(_gemini_returning_text(json.dumps(raw)))
    intent = await classifier.classify("bu haftaki maillerime bak")
    assert intent.type == "mail"
    assert intent.payload["range_kind"] == "weekly"


@pytest.mark.asyncio
async def test_classifier_falls_back_when_mail_range_kind_unsupported() -> None:
    """Custom range from chat / voice should bounce — the user has to
    pick custom dates from the shortcut UI."""
    raw = {"type": "mail", "payload": {"range_kind": "custom"}}
    classifier = Classifier(_gemini_returning_text(json.dumps(raw)))
    intent = await classifier.classify("4 nisan ile 5 nisan arası mailler")
    assert intent.type == "fallback"


@pytest.mark.asyncio
async def test_classifier_falls_back_when_mail_payload_missing_range() -> None:
    raw = {"type": "mail", "payload": {}}
    classifier = Classifier(_gemini_returning_text(json.dumps(raw)))
    intent = await classifier.classify("mail")
    assert intent.type == "fallback"


@pytest.mark.asyncio
async def test_classifier_includes_now_in_system_prompt() -> None:
    """The model needs the current timestamp to resolve "yarın", "Cuma", etc.
    Verify that whatever ``now_factory`` returns ends up in the prompt."""
    from datetime import datetime

    captured: dict[str, str] = {}

    async def fake_generate_json(prompt, *, system=None):
        captured["system"] = system or ""
        return {"type": "fallback", "payload": {}}

    client = _gemini_returning_text(json.dumps({"type": "fallback", "payload": {}}))
    client.generate_json = fake_generate_json  # type: ignore[method-assign]

    frozen = datetime(2026, 4, 27, 9, 30, tzinfo=UTC)
    classifier = Classifier(client, now_factory=lambda: frozen)
    await classifier.classify("yarın toplantı ekle")
    assert "2026-04-27T09:30:00+00:00" in captured["system"]
