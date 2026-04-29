"""JournalReportStrategy — proxies tag commands to the Journal AI Reporter.

User types something like ``/detail`` or ``/date{15.04.2026}`` in Jarvis chat.
Classifier alone may not catch it (the tags are project-specific syntax), so
this strategy *also* recognises tag patterns directly from the intent text.
On a hit it POSTs to the Reporter Bridge ``/report`` endpoint and surfaces
the markdown back to the user.

Two boundaries we hold:
- never log the journal payload (PII)
- never raise — convert transport / auth / rate-limit errors into Error
  results with friendly Turkish messages
"""
from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any

import httpx

from core.base_strategy import CapabilityStrategy
from core.result import Error, Result, Success

logger = logging.getLogger(__name__)


# Whitelist + /date{...} pattern. Matched against the *start* of a stripped
# message so a user typing "/detail son 7 gün" still routes here.
_BASE_TAGS: tuple[str, ...] = ("/detail", "/todo", "/concern", "/success")
_DATE_TAG_RE = re.compile(r"^/date\{(\d{2})\.(\d{2})\.(\d{4})\}")
_LAST_N_DAYS_RE = re.compile(r"son\s+(\d+)\s+gün", re.IGNORECASE)


class JournalReportStrategy(CapabilityStrategy):
    name = "journal"
    intent_keys = ("journal", "günlük", "diary", "/detail", "/todo", "/concern", "/success", "/date")

    def __init__(
        self,
        reporter_url: str,
        reporter_key: str,
        *,
        timeout: float = 90.0,
        client_factory=None,
    ) -> None:
        self._reporter_url = reporter_url.rstrip("/")
        self._reporter_key = reporter_key
        self._timeout = timeout
        # Tests inject a fake client factory; production uses the default.
        self._client_factory = client_factory or self._default_client_factory

    def _default_client_factory(self):
        return httpx.AsyncClient(timeout=self._timeout)

    def can_handle(self, intent: dict[str, Any]) -> bool:
        if intent.get("type") == "journal":
            return True
        text = (intent.get("text") or "").strip()
        return _extract_tag(text) is not None

    async def execute(self, payload: dict[str, Any]) -> Result:
        text = (payload.get("text") or "").strip()
        tag = _extract_tag(text)
        if tag is None:
            return Error(
                message="no journal tag detected",
                user_message="Hangi günlük komutunu istediğini anlamadım (/detail, /todo, /concern, /success, /date{gg.aa.yyyy}).",
                user_notify=True,
                log_level="info",
            )

        body: dict[str, Any] = {"tag": tag}
        date_range = _extract_range(text)
        if date_range is not None:
            body["date_range"] = date_range

        if not self._reporter_url or not self._reporter_key:
            return Error(
                message="reporter not configured",
                user_message="Journal Reporter şu an yapılandırılmamış. Yöneticine söyle.",
                user_notify=True,
                log_level="warning",
            )

        try:
            async with self._client_factory() as client:
                response = await client.post(
                    f"{self._reporter_url}/report",
                    json=body,
                    headers={"Authorization": f"Bearer {self._reporter_key}"},
                )
        except httpx.TimeoutException:
            return Error(
                message="reporter timeout",
                user_message="Journal Reporter şu an yanıt vermiyor, biraz sonra dene.",
                retry_after=15,
            )
        except httpx.RequestError as exc:
            logger.warning("journal reporter unreachable: %s", exc)
            return Error(
                message=f"reporter unreachable: {exc}",
                user_message="Journal Reporter'a ulaşamıyorum, biraz sonra dene.",
                retry_after=15,
            )

        if response.status_code == 200:
            data = response.json()
            return Success(
                data={
                    "tag": data.get("tag", tag),
                    "markdown": data.get("raw_markdown", ""),
                    "entry_count": data.get("entry_count", 0),
                    "date_range": data.get("date_range"),
                },
                ui_type="JournalReportCard",
            )

        return _http_error_to_result(response, tag=tag)

    def render_hint(self) -> str:
        return "JournalReportCard"


def _extract_tag(text: str) -> str | None:
    if not text:
        return None
    head = text.strip()
    for base in _BASE_TAGS:
        # Match whole-word boundary so "/detailed" doesn't fire /detail.
        if head == base or head.startswith(base + " ") or head.startswith(base + "\n"):
            return base
    if _DATE_TAG_RE.match(head):
        # Extract just the tag, dropping trailing words.
        m = _DATE_TAG_RE.match(head)
        return f"/date{{{m.group(1)}.{m.group(2)}.{m.group(3)}}}"
    return None


def _extract_range(text: str) -> dict[str, str] | None:
    """Best-effort: only `son N gün` recognised today.

    The user can also send a /date tag, which conveys its own range and
    skips this path. Anything else falls back to the Reporter's default
    (last 30 days).
    """
    m = _LAST_N_DAYS_RE.search(text)
    if not m:
        return None
    n = int(m.group(1))
    if n <= 0 or n > 365:
        return None
    from datetime import timedelta

    end = date.today()
    start = end - timedelta(days=n - 1)
    return {"start": start.isoformat(), "end": end.isoformat()}


def _http_error_to_result(response: httpx.Response, *, tag: str) -> Error:
    try:
        body = response.json()
        code = body.get("code") if isinstance(body, dict) else None
        upstream_msg = body.get("message") if isinstance(body, dict) else None
    except ValueError:
        code = None
        upstream_msg = None

    status = response.status_code
    if status == 401:
        return Error(
            message="reporter auth failed",
            user_message="Journal Reporter kimlik doğrulaması başarısız.",
            user_notify=True,
            log_level="error",
        )
    if status == 404:
        if code == "date_not_in_range":
            return Error(
                message="date not in range",
                user_message=f"{tag} için aralıkta giriş yok.",
                user_notify=True,
                log_level="info",
            )
        return Error(
            message="no entries",
            user_message="Bu aralıkta günlük girişi bulamadım.",
            user_notify=True,
            log_level="info",
        )
    if status == 429:
        return Error(
            message="reporter rate limited",
            user_message="Çok hızlı istek attın, biraz bekle.",
            retry_after=30,
        )
    if status in (502, 503):
        return Error(
            message=f"reporter upstream {status}",
            user_message="Journal Reporter şu an erişilemiyor (Cornell veya Gemini düştü).",
            retry_after=30,
        )
    return Error(
        message=f"reporter http {status}: {upstream_msg or 'unknown'}",
        user_message="Journal Reporter beklenmedik bir cevap döndü.",
        user_notify=True,
        log_level="error",
    )
