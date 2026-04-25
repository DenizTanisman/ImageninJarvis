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


def _strategy(*, oauth, classifier, cache, adapter) -> MailStrategy:
    return MailStrategy(
        oauth=oauth,
        classifier=classifier,
        cache=cache,
        adapter_factory=lambda creds: adapter,
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
async def test_returns_error_when_range_missing(cache: EmailCache) -> None:
    oauth = _oauth_with_credentials(MagicMock())
    strategy = _strategy(
        oauth=oauth,
        classifier=_classifier_returning([]),
        cache=cache,
        adapter=_adapter_returning([]),
    )
    result = await strategy.execute({"range_kind": "daily"})
    assert isinstance(result, Error)


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
