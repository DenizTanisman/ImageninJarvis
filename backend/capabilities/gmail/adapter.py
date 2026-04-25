"""Gmail API wrapper.

Calls Google's Gmail v1 API with a pre-built ``Credentials`` object.
Only metadata + snippet is fetched (no message body) to keep token /
quota usage low; the classifier in 2.5 sees enough text to bucket the
mail without paying for the full payload.
"""
from __future__ import annotations

import logging
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import MailSummary

logger = logging.getLogger(__name__)

DEFAULT_MAX_RESULTS = 30
METADATA_HEADERS = ("From", "Subject", "Date")


class GmailAdapterError(RuntimeError):
    pass


class GmailAdapter:
    """Thin synchronous wrapper around Gmail v1.

    Sync rather than async because google-api-python-client is sync; we
    call adapter methods from a thread / executor when used from FastAPI.
    """

    def __init__(self, credentials: Credentials, *, service: Any | None = None) -> None:
        if service is not None:
            self._service = service
        else:
            self._service = build(
                "gmail", "v1", credentials=credentials, cache_discovery=False
            )

    def list_messages(
        self,
        *,
        after: str,
        before: str,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> list[MailSummary]:
        """Return up to ``max_results`` messages dated in ``[after, before)``.

        ``after`` / ``before`` are ``YYYY-MM-DD`` strings interpreted by
        Gmail's search syntax (timezone is the user's mailbox tz).
        """
        if max_results <= 0:
            return []
        query = f"after:{after} before:{before}"
        try:
            list_resp = (
                self._service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
        except HttpError as exc:
            raise GmailAdapterError(f"Gmail list failed: {exc}") from exc

        ids = [m["id"] for m in list_resp.get("messages", []) if "id" in m]
        summaries: list[MailSummary] = []
        for message_id in ids:
            try:
                payload = (
                    self._service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=message_id,
                        format="metadata",
                        metadataHeaders=list(METADATA_HEADERS),
                    )
                    .execute()
                )
            except HttpError as exc:
                logger.warning("Skipping mail %s: %s", message_id, exc)
                continue
            summary = _parse_metadata(payload)
            if summary is not None:
                summaries.append(summary)
        return summaries


def _parse_metadata(payload: dict[str, Any]) -> MailSummary | None:
    headers_list = payload.get("payload", {}).get("headers", [])
    headers: dict[str, str] = {h["name"].lower(): h["value"] for h in headers_list}
    try:
        return MailSummary(
            id=payload["id"],
            thread_id=payload.get("threadId", ""),
            from_addr=headers.get("from", ""),
            subject=headers.get("subject", "(no subject)"),
            snippet=payload.get("snippet", ""),
            date=headers.get("date", ""),
            internal_date_ms=int(payload.get("internalDate", "0") or 0),
        )
    except KeyError:
        return None
