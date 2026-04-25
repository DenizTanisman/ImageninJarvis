from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from capabilities.gmail.classifier import (
    EMAIL_CLASSIFIER_SYSTEM_PROMPT,
    ClassifiedMail,
    EmailClassifier,
    EmailClassifierError,
)
from capabilities.gmail.models import MailSummary
from services.gemini_client import GeminiClient, GeminiUnavailable


def _mail(msg_id: str, subject: str = "subj", from_addr: str = "a@example.com") -> MailSummary:
    return MailSummary(
        id=msg_id,
        thread_id="t",
        from_addr=from_addr,
        subject=subject,
        snippet="snippet",
        date="2026-04-25",
        internal_date_ms=1745835600000,
    )


def _gemini_with_json(payload: object) -> tuple[GeminiClient, AsyncMock]:
    """Stub a GeminiClient whose generate_json returns the given payload."""
    model = AsyncMock()
    # Keep generate_text working; tests below override generate_json directly.
    model.generate_content_async.return_value = SimpleNamespace(text="{}")
    client = GeminiClient(model=model, max_concurrent=2, max_attempts=1)

    async def fake_json(prompt: str, *, system: str | None = None):
        # Capture the system prompt + user message shape on the mock so tests can assert on them.
        fake_json.last_prompt = prompt
        fake_json.last_system = system
        return payload

    fake_json.last_prompt = None  # type: ignore[attr-defined]
    fake_json.last_system = None  # type: ignore[attr-defined]
    client.generate_json = fake_json  # type: ignore[method-assign]
    return client, model


@pytest.mark.asyncio
async def test_classify_empty_batch_returns_empty_list() -> None:
    client, _ = _gemini_with_json([])
    classifier = EmailClassifier(client)
    assert await classifier.classify_batch([]) == []


@pytest.mark.asyncio
async def test_classify_buckets_five_mails_correctly() -> None:
    mails = [_mail(f"m{i}") for i in range(1, 6)]
    payload = [
        {"id": "m1", "category": "important", "confidence": 0.95, "summary": "Acil rapor", "needs_reply": True},
        {"id": "m2", "category": "dm", "confidence": 0.9, "summary": "Soru var", "needs_reply": True},
        {"id": "m3", "category": "promo", "confidence": 0.92, "summary": "Kampanya", "needs_reply": False},
        {"id": "m4", "category": "other", "confidence": 0.95, "summary": "Sistem raporu", "needs_reply": False},
        {"id": "m5", "category": "important", "confidence": 0.6, "summary": "Belirsiz", "needs_reply": False},
    ]
    client, _ = _gemini_with_json(payload)
    classifier = EmailClassifier(client)
    results = await classifier.classify_batch(mails)
    by_id = {r.mail.id: r for r in results}
    assert by_id["m1"].category == "important"
    assert by_id["m1"].needs_reply is True
    assert by_id["m2"].category == "dm"
    assert by_id["m3"].category == "promo"
    assert by_id["m4"].category == "other"
    # Below confidence threshold falls back to other.
    assert by_id["m5"].category == "other"


@pytest.mark.asyncio
async def test_classify_falls_back_to_other_when_model_drops_a_mail() -> None:
    mails = [_mail("m1"), _mail("m2")]
    client, _ = _gemini_with_json(
        [{"id": "m1", "category": "important", "confidence": 0.95, "summary": "x", "needs_reply": False}]
    )
    classifier = EmailClassifier(client)
    results = await classifier.classify_batch(mails)
    by_id = {r.mail.id: r for r in results}
    assert by_id["m2"].category == "other"
    assert by_id["m2"].confidence == 0.0


@pytest.mark.asyncio
async def test_classify_clamps_invalid_category_to_other() -> None:
    mails = [_mail("m1")]
    client, _ = _gemini_with_json(
        [{"id": "m1", "category": "spam", "confidence": 0.95, "summary": "x", "needs_reply": False}]
    )
    classifier = EmailClassifier(client)
    out = await classifier.classify_batch(mails)
    assert out[0].category == "other"


@pytest.mark.asyncio
async def test_classify_passes_user_content_with_wrapping_tags() -> None:
    mails = [_mail("m1", subject="Önemli toplantı")]
    client, _ = _gemini_with_json(
        [{"id": "m1", "category": "important", "confidence": 0.95, "summary": "x", "needs_reply": False}]
    )
    classifier = EmailClassifier(client)
    await classifier.classify_batch(mails)
    sent_prompt = client.generate_json.last_prompt  # type: ignore[attr-defined]
    sent_system = client.generate_json.last_system  # type: ignore[attr-defined]
    assert "<user_content>" in sent_prompt and "</user_content>" in sent_prompt
    assert "Önemli toplantı" in sent_prompt
    assert sent_system == EMAIL_CLASSIFIER_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_classify_raises_when_gemini_unavailable() -> None:
    client, _ = _gemini_with_json([])

    async def boom(*_args, **_kwargs):
        raise GeminiUnavailable("offline")

    client.generate_json = boom  # type: ignore[method-assign]
    classifier = EmailClassifier(client)
    with pytest.raises(EmailClassifierError):
        await classifier.classify_batch([_mail("m1")])


@pytest.mark.asyncio
async def test_classify_raises_when_response_not_array() -> None:
    client, _ = _gemini_with_json({"id": "m1", "category": "important"})
    classifier = EmailClassifier(client)
    with pytest.raises(EmailClassifierError):
        await classifier.classify_batch([_mail("m1")])


@pytest.mark.asyncio
async def test_classify_returns_classified_mail_dataclass() -> None:
    mails = [_mail("m1")]
    client, _ = _gemini_with_json(
        [{"id": "m1", "category": "dm", "confidence": 0.92, "summary": "S", "needs_reply": True}]
    )
    classifier = EmailClassifier(client)
    [result] = await classifier.classify_batch(mails)
    assert isinstance(result, ClassifiedMail)
    assert result.mail.id == "m1"
    assert result.summary == "S"
