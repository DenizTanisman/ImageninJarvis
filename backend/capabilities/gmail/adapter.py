"""Gmail API wrapper.

Calls Google's Gmail v1 API with a pre-built ``Credentials`` object.
Only metadata + snippet is fetched in ``list_messages`` to keep token /
quota usage low; full bodies are pulled lazily via ``get_full_message``
when a draft needs context, and ``send_reply`` posts an RFC-2822 reply
threaded with the original.
"""
from __future__ import annotations

import base64
import logging
from email.message import EmailMessage
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import MailSummary

logger = logging.getLogger(__name__)

DEFAULT_MAX_RESULTS = 30
METADATA_HEADERS = ("From", "Subject", "Date")
# googleapiclient's HttpRequest.execute() retries on its own when this is >0.
# Covers transient TLS / connection resets we hit on macOS Python 3.13.
EXECUTE_NUM_RETRIES = 3


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
                .execute(num_retries=EXECUTE_NUM_RETRIES)
            )
        except (HttpError, OSError) as exc:
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
                    .execute(num_retries=EXECUTE_NUM_RETRIES)
                )
            except (HttpError, OSError) as exc:
                logger.warning("Skipping mail %s: %s", message_id, exc)
                continue
            summary = _parse_metadata(payload)
            if summary is not None:
                summaries.append(summary)
        return summaries


    def get_full_message(self, message_id: str) -> dict[str, Any]:
        """Fetch the full message including the body text — used by the
        draft generator for grounding context. Body parts are returned
        as base64url strings (Google's encoding); call sites decode."""
        try:
            return (
                self._service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute(num_retries=EXECUTE_NUM_RETRIES)
            )
        except (HttpError, OSError) as exc:
            raise GmailAdapterError(f"Gmail get failed: {exc}") from exc

    def send_new(
        self,
        *,
        to: str,
        subject: str,
        body: str,
    ) -> dict[str, Any]:
        """Send a brand-new email — no thread, no ``Re:`` prefix.

        Used by the chat-driven compose flow ("X'e mail at"). Caller is
        expected to pre-validate the recipient and to surface the draft
        to the user before invoking; nothing here gates against missing
        confirmation.
        """
        if not to or not body.strip():
            raise GmailAdapterError("send_new requires a recipient and body")
        message = EmailMessage()
        message["To"] = to
        message["Subject"] = subject or "(konusuz)"
        message.set_content(body)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        try:
            return (
                self._service.users()
                .messages()
                .send(userId="me", body={"raw": raw})
                .execute(num_retries=EXECUTE_NUM_RETRIES)
            )
        except (HttpError, OSError) as exc:
            raise GmailAdapterError(f"Gmail send failed: {exc}") from exc

    def send_reply(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        thread_id: str,
        in_reply_to_message_id: str | None = None,
    ) -> dict[str, Any]:
        """Send a plain-text reply on an existing thread.

        ``in_reply_to_message_id`` should be the RFC-822 Message-Id header
        of the message we're replying to (not the Gmail internal id) so
        clients thread it; pass None to skip threading headers.
        """
        if not to or not body.strip():
            raise GmailAdapterError("send_reply requires a recipient and body")
        message = EmailMessage()
        message["To"] = to
        message["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        if in_reply_to_message_id:
            message["In-Reply-To"] = in_reply_to_message_id
            message["References"] = in_reply_to_message_id
        message.set_content(body)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        try:
            return (
                self._service.users()
                .messages()
                .send(userId="me", body={"raw": raw, "threadId": thread_id})
                .execute(num_retries=EXECUTE_NUM_RETRIES)
            )
        except (HttpError, OSError) as exc:
            raise GmailAdapterError(f"Gmail send failed: {exc}") from exc


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
