"""MailStrategy aggregates adapter + classifier + cache into a single Result."""
from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from core.base_strategy import CapabilityStrategy
from core.result import Error, Result, Success
from services.auth_oauth import GoogleOAuthService
from services.cache_sqlite import EmailCache, build_mail_key

from .adapter import GmailAdapter, GmailAdapterError
from .classifier import EmailClassifier, EmailClassifierError
from .models import MailSummary

# Voice / chat intents arrive without explicit dates — the LLM gives us
# range_kind and we compute the window. Daily = today, Weekly = past 7
# days. Gmail's "before" filter is inclusive of date strings on the day
# boundary, so we use "tomorrow" as the upper bound to include today.
DEFAULT_WEEKLY_DAYS = 7

logger = logging.getLogger(__name__)


class MailStrategy(CapabilityStrategy):
    name = "mail"
    intent_keys = ("mail", "gmail", "inbox", "mailler")

    def __init__(
        self,
        *,
        oauth: GoogleOAuthService,
        classifier: EmailClassifier,
        cache: EmailCache,
        adapter_factory=None,
        now_factory=None,
    ) -> None:
        self._oauth = oauth
        self._classifier = classifier
        self._cache = cache
        # Tests can inject ``adapter_factory(credentials) -> GmailAdapter`` to
        # avoid the real google-api-python-client build call.
        self._adapter_factory = adapter_factory or (lambda creds: GmailAdapter(creds))
        # Tests freeze "today" so date defaulting is deterministic; runtime
        # uses the wall clock.
        self._now_factory = now_factory or (lambda: datetime.now(UTC).date())

    def can_handle(self, intent: dict[str, Any]) -> bool:
        return intent.get("type") == "mail"

    async def execute(self, payload: dict[str, Any]) -> Result:
        kind = payload.get("range_kind", "daily")
        after = payload.get("after")
        before = payload.get("before")
        # Voice / chat intents only ship range_kind; compute the window
        # from "today" so the dispatcher path doesn't need to know dates.
        if not after or not before:
            computed = _resolve_range(kind, today=self._now_factory())
            if computed is None:
                return Error(
                    message="missing range bounds",
                    user_message="Mail aralığı belirtilmedi.",
                    user_notify=True,
                    log_level="warning",
                )
            after, before = computed
        max_results = int(payload.get("max_results") or 30)
        user_id = payload.get("user_id", "default")

        cache_key = build_mail_key(
            user_id=user_id, kind=str(kind), after=str(after), before=str(before)
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            return Success(data=cached, ui_type="MailCard", meta={"source": "cache"})

        try:
            credentials = self._oauth.credentials_for(user_id=user_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Credential refresh failed: %s", exc)
            return Error(
                message=str(exc),
                user_message="Google bağlantın yenilenemedi, tekrar bağlan.",
                retry_after=None,
            )
        if credentials is None:
            return Error(
                message="not connected",
                user_message="Google'a bağlı değilsin. Önce mail erişimi için bağlan.",
                user_notify=True,
                log_level="info",
            )

        adapter = self._adapter_factory(credentials)
        try:
            mails: list[MailSummary] = adapter.list_messages(
                after=after, before=before, max_results=max_results
            )
        except GmailAdapterError as exc:
            logger.error("Gmail list failed: %s", exc)
            return Error(
                message=str(exc),
                user_message="Mailler çekilirken bir sorun oldu.",
                retry_after=10,
            )

        try:
            classified = await self._classifier.classify_batch(mails)
        except EmailClassifierError as exc:
            logger.error("Classifier failed: %s", exc)
            return Error(
                message=str(exc),
                user_message="Mailler kategorize edilemedi, biraz sonra tekrar dener misin?",
                retry_after=15,
            )

        bucket: dict[str, list[dict[str, Any]]] = {
            "important": [],
            "dm": [],
            "promo": [],
            "other": [],
        }
        needs_reply = 0
        for item in classified:
            entry = {
                "id": item.mail.id,
                "from": item.mail.from_addr,
                "subject": item.mail.subject,
                "snippet": item.mail.snippet,
                "summary": item.summary,
                "needs_reply": item.needs_reply,
                "confidence": item.confidence,
                "thread_id": item.mail.thread_id,
            }
            bucket[item.category].append(entry)
            if item.needs_reply:
                needs_reply += 1

        body = {
            "range": {"kind": kind, "after": after, "before": before},
            "categories": bucket,
            "needs_reply_count": needs_reply,
            "total": len(classified),
        }
        self._cache.put(cache_key, body)
        return Success(data=body, ui_type="MailCard", meta={"source": "live"})

    def render_hint(self) -> str:
        return "MailCard"


def serialize_mail_summary(mail: MailSummary) -> dict[str, Any]:
    return asdict(mail)


def _resolve_range(kind: Any, *, today: date) -> tuple[str, str] | None:
    """Convert ``range_kind`` into Gmail-search-compatible YYYY-MM-DD
    bounds. ``custom`` requires explicit dates the caller already
    provided, so an unresolved custom returns None to trigger the
    "missing bounds" error path."""
    if kind == "daily":
        after = today
    elif kind == "weekly":
        after = today - timedelta(days=DEFAULT_WEEKLY_DAYS - 1)
    else:
        return None
    before = today + timedelta(days=1)
    return after.isoformat(), before.isoformat()
