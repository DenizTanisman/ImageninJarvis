from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.fernet import Fernet

from capabilities.gmail.classifier import ClassifiedMail, EmailClassifier
from capabilities.gmail.models import MailSummary
from capabilities.gmail.strategy import MailStrategy
from core.result import Error, Success
from services.auth_oauth import GoogleOAuthService
from services.cache_sqlite import EmailCache
from services.gemini_client import GeminiClient
from services.token_store import TokenStore


def _mail(msg_id: str, subject: str = "subj") -> MailSummary:
    return MailSummary(
        id=msg_id,
        thread_id="t",
        from_addr=f"{msg_id}@example.com",
        subject=subject,
        snippet="snippet",
        date="Tue, 28 Apr 2026 10:00:00 +0300",
        internal_date_ms=1745835600000,
    )


@pytest.fixture()
def cache(tmp_path) -> EmailCache:
    return EmailCache(tmp_path / "cache.db")


@pytest.fixture()
def token_store(tmp_path) -> TokenStore:
    return TokenStore(tmp_path / "tokens.db", Fernet.generate_key().decode())


def _oauth_with_credentials(creds) -> MagicMock:
    fake = MagicMock(spec=GoogleOAuthService)
    fake.credentials_for.return_value = creds
    return fake


def _gemini_with_classify(classified: list[ClassifiedMail]) -> tuple[GeminiClient, MagicMock]:
    model = AsyncMock()
    model.generate_content_async.return_value = SimpleNamespace(text="[]")
    client = GeminiClient(model=model, max_concurrent=2, max_attempts=1)
    return client, model


def _classifier_returning(classified: list[ClassifiedMail]) -> MagicMock:
    fake = MagicMock(spec=EmailClassifier)
    fake.classify_batch = AsyncMock(return_value=classified)
    return fake


def _adapter_returning(mails: list[MailSummary]) -> MagicMock:
    adapter = MagicMock()
    adapter.list_messages.return_value = mails
    return adapter


def _strategy(*, oauth, classifier, cache, adapter, now_factory=None) -> MailStrategy:
    return MailStrategy(
        oauth=oauth,
        classifier=classifier,
        cache=cache,
        adapter_factory=lambda creds: adapter,
        now_factory=now_factory,
    )


@pytest.mark.asyncio
async def test_returns_error_when_user_not_connected(cache: EmailCache) -> None:
    oauth = _oauth_with_credentials(None)
    strategy = _strategy(
        oauth=oauth,
        classifier=_classifier_returning([]),
        cache=cache,
        adapter=_adapter_returning([]),
    )
    result = await strategy.execute(
        {"range_kind": "daily", "after": "2026-04-24", "before": "2026-04-25"}
    )
    assert isinstance(result, Error)
    assert "bağlı" in result.user_message.lower()


@pytest.mark.asyncio
async def test_returns_error_when_range_kind_unknown(cache: EmailCache) -> None:
    """Custom range without explicit dates can't be auto-resolved — the
    /mail/summary shortcut always sends explicit dates, but the chat /
    voice path goes through the classifier which only ships
    daily / weekly. Anything else falls into the "missing bounds" error."""
    oauth = _oauth_with_credentials(MagicMock())
    strategy = _strategy(
        oauth=oauth,
        classifier=_classifier_returning([]),
        cache=cache,
        adapter=_adapter_returning([]),
    )
    result = await strategy.execute({"range_kind": "custom"})
    assert isinstance(result, Error)


@pytest.mark.asyncio
async def test_resolves_daily_range_from_today_when_dates_omitted(
    cache: EmailCache,
) -> None:
    """Voice / chat intents only ship range_kind; the strategy must
    compute YYYY-MM-DD bounds itself."""
    import datetime as _dt

    frozen = _dt.date(2026, 4, 27)
    adapter = _adapter_returning([])
    strategy = _strategy(
        oauth=_oauth_with_credentials(MagicMock()),
        classifier=_classifier_returning([]),
        cache=cache,
        adapter=adapter,
        now_factory=lambda: frozen,
    )
    result = await strategy.execute({"range_kind": "daily"})
    assert isinstance(result, Success)
    adapter_inst = strategy._adapter_factory(MagicMock())
    # Adapter was called with today=2026-04-27, before=2026-04-28
    adapter_inst.list_messages.assert_called()
    kwargs = adapter_inst.list_messages.call_args.kwargs
    assert kwargs["after"] == "2026-04-27"
    assert kwargs["before"] == "2026-04-28"


@pytest.mark.asyncio
async def test_resolves_weekly_range_to_last_seven_days(cache: EmailCache) -> None:
    import datetime as _dt

    frozen = _dt.date(2026, 4, 27)
    adapter = _adapter_returning([])
    strategy = _strategy(
        oauth=_oauth_with_credentials(MagicMock()),
        classifier=_classifier_returning([]),
        cache=cache,
        adapter=adapter,
        now_factory=lambda: frozen,
    )
    result = await strategy.execute({"range_kind": "weekly"})
    assert isinstance(result, Success)
    adapter_inst = strategy._adapter_factory(MagicMock())
    kwargs = adapter_inst.list_messages.call_args.kwargs
    assert kwargs["after"] == "2026-04-21"
    assert kwargs["before"] == "2026-04-28"


@pytest.mark.asyncio
async def test_happy_path_buckets_mails(cache: EmailCache) -> None:
    mails = [_mail("m1"), _mail("m2"), _mail("m3")]
    classified = [
        ClassifiedMail(mail=mails[0], category="important", confidence=0.95, summary="Acil", needs_reply=True),
        ClassifiedMail(mail=mails[1], category="dm", confidence=0.9, summary="Soru", needs_reply=True),
        ClassifiedMail(mail=mails[2], category="promo", confidence=0.92, summary="Kampanya", needs_reply=False),
    ]
    strategy = _strategy(
        oauth=_oauth_with_credentials(MagicMock()),
        classifier=_classifier_returning(classified),
        cache=cache,
        adapter=_adapter_returning(mails),
    )
    result = await strategy.execute(
        {"range_kind": "daily", "after": "2026-04-24", "before": "2026-04-25"}
    )
    assert isinstance(result, Success)
    assert result.ui_type == "MailCard"
    cats = result.data["categories"]
    assert len(cats["important"]) == 1
    assert len(cats["dm"]) == 1
    assert len(cats["promo"]) == 1
    assert cats["other"] == []
    assert result.data["needs_reply_count"] == 2
    assert result.data["total"] == 3
    assert result.meta == {"source": "live"}


@pytest.mark.asyncio
async def test_second_call_returns_cached(cache: EmailCache) -> None:
    mails = [_mail("m1")]
    classified = [
        ClassifiedMail(mail=mails[0], category="important", confidence=0.95, summary="x", needs_reply=False),
    ]
    classifier = _classifier_returning(classified)
    adapter = _adapter_returning(mails)
    strategy = _strategy(
        oauth=_oauth_with_credentials(MagicMock()),
        classifier=classifier,
        cache=cache,
        adapter=adapter,
    )
    payload = {"range_kind": "daily", "after": "2026-04-24", "before": "2026-04-25"}
    first = await strategy.execute(payload)
    second = await strategy.execute(payload)
    assert isinstance(first, Success) and first.meta == {"source": "live"}
    assert isinstance(second, Success) and second.meta == {"source": "cache"}
    classifier.classify_batch.assert_awaited_once()
    adapter.list_messages.assert_called_once()


@pytest.mark.asyncio
async def test_classifier_failure_surfaces_friendly_error(cache: EmailCache) -> None:
    from capabilities.gmail.classifier import EmailClassifierError

    classifier = MagicMock(spec=EmailClassifier)
    classifier.classify_batch = AsyncMock(side_effect=EmailClassifierError("offline"))
    strategy = _strategy(
        oauth=_oauth_with_credentials(MagicMock()),
        classifier=classifier,
        cache=cache,
        adapter=_adapter_returning([_mail("m1")]),
    )
    result = await strategy.execute(
        {"range_kind": "daily", "after": "2026-04-24", "before": "2026-04-25"}
    )
    assert isinstance(result, Error)
    assert result.retry_after == 15


@pytest.mark.asyncio
async def test_adapter_failure_surfaces_friendly_error(cache: EmailCache) -> None:
    from capabilities.gmail.adapter import GmailAdapterError

    adapter = MagicMock()
    adapter.list_messages.side_effect = GmailAdapterError("unavailable")
    strategy = _strategy(
        oauth=_oauth_with_credentials(MagicMock()),
        classifier=_classifier_returning([]),
        cache=cache,
        adapter=adapter,
    )
    result = await strategy.execute(
        {"range_kind": "daily", "after": "2026-04-24", "before": "2026-04-25"}
    )
    assert isinstance(result, Error)


# ---------- compose ----------


def _draft_generator_returning(subject: str, body: str) -> MagicMock:
    from capabilities.gmail.draft import ComposeDraft, DraftGenerator

    fake = MagicMock(spec=DraftGenerator)

    async def _gen(*, to: str, instruction: str) -> ComposeDraft:
        return ComposeDraft(to=to, subject=subject, body=body)

    fake.generate_compose = _gen
    return fake


def _strategy_with_draft(
    *, oauth, cache: EmailCache, draft_generator: MagicMock
) -> MailStrategy:
    return MailStrategy(
        oauth=oauth,
        classifier=_classifier_returning([]),
        cache=cache,
        adapter_factory=lambda creds: MagicMock(),
        draft_generator=draft_generator,
    )


@pytest.mark.asyncio
async def test_compose_returns_draft_card(cache: EmailCache) -> None:
    strategy = _strategy_with_draft(
        oauth=_oauth_with_credentials(MagicMock()),
        cache=cache,
        draft_generator=_draft_generator_returning(
            "Merhaba", "Merhaba,\n\nKısa bir selam.\n\nİyi çalışmalar."
        ),
    )
    result = await strategy.execute(
        {
            "action": "compose",
            "to": "ali@example.com",
            "instruction": "merhaba yaz",
        }
    )
    assert isinstance(result, Success)
    assert result.ui_type == "MailDraftCard"
    assert result.meta == {"action": "compose"}
    assert result.data["to"] == "ali@example.com"
    assert result.data["subject"] == "Merhaba"
    assert "selam" in result.data["body"].lower()


@pytest.mark.asyncio
async def test_compose_rejects_invalid_recipient(cache: EmailCache) -> None:
    strategy = _strategy_with_draft(
        oauth=_oauth_with_credentials(MagicMock()),
        cache=cache,
        draft_generator=_draft_generator_returning("x", "y"),
    )
    result = await strategy.execute(
        {"action": "compose", "to": "not-an-email", "instruction": "merhaba"}
    )
    assert isinstance(result, Error)


@pytest.mark.asyncio
async def test_compose_rejects_empty_instruction(cache: EmailCache) -> None:
    strategy = _strategy_with_draft(
        oauth=_oauth_with_credentials(MagicMock()),
        cache=cache,
        draft_generator=_draft_generator_returning("x", "y"),
    )
    result = await strategy.execute(
        {"action": "compose", "to": "ali@example.com", "instruction": "  "}
    )
    assert isinstance(result, Error)


@pytest.mark.asyncio
async def test_compose_errors_when_draft_generator_unavailable(
    cache: EmailCache,
) -> None:
    """A misconfigured registry shouldn't crash — surface a friendly Error."""
    strategy = MailStrategy(
        oauth=_oauth_with_credentials(MagicMock()),
        classifier=_classifier_returning([]),
        cache=cache,
        adapter_factory=lambda creds: MagicMock(),
        # draft_generator omitted on purpose
    )
    result = await strategy.execute(
        {"action": "compose", "to": "ali@example.com", "instruction": "selam"}
    )
    assert isinstance(result, Error)


@pytest.mark.asyncio
async def test_compose_surfaces_friendly_error_when_gemini_fails(
    cache: EmailCache,
) -> None:
    from capabilities.gmail.draft import DraftGenerator, DraftGeneratorError

    fake = MagicMock(spec=DraftGenerator)

    async def _boom(*, to, instruction):
        raise DraftGeneratorError("gemini offline")

    fake.generate_compose = _boom
    strategy = _strategy_with_draft(
        oauth=_oauth_with_credentials(MagicMock()),
        cache=cache,
        draft_generator=fake,
    )
    result = await strategy.execute(
        {"action": "compose", "to": "ali@example.com", "instruction": "selam"}
    )
    assert isinstance(result, Error)
    assert result.retry_after == 10
