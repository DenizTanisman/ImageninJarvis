"""Mail HTTP routes.

- POST /mail/summary  — list + classify a range
- POST /mail/drafts   — generate reply drafts for selected message ids
- POST /mail/send     — actually send an (approved) reply (one at a time)
- GET  /mail/auth-status — does the user have valid Google credentials?

Sending mail is per-message and per-confirmation per CLAUDE.md §2.7.
The frontend renders each draft, lets the user edit, and posts /mail/send
only after explicit approval.
"""
from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies import (
    get_draft_generator,
    get_gmail_adapter_factory,
    get_mail_strategy,
    get_oauth_service,
)
from app.schemas import ChatErrorPayload, ChatResponse
from capabilities.gmail.adapter import GmailAdapterError
from capabilities.gmail.draft import DraftGenerator, DraftGeneratorError
from capabilities.gmail.strategy import MailStrategy
from core.result import Error, Success
from services.auth_oauth import (
    GMAIL_SEND_SCOPES,
    GoogleOAuthService,
    has_required_scopes,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mail", tags=["mail"])

MailStrategyDep = Annotated[MailStrategy, Depends(get_mail_strategy)]
OAuthDep = Annotated[GoogleOAuthService, Depends(get_oauth_service)]
DraftDep = Annotated[DraftGenerator, Depends(get_draft_generator)]
AdapterFactoryDep = Annotated[object, Depends(get_gmail_adapter_factory)]


class MailSummaryRequest(BaseModel):
    range_kind: Literal["daily", "weekly", "custom"] = "daily"
    after: str = Field(..., min_length=10, max_length=10)
    before: str = Field(..., min_length=10, max_length=10)
    max_results: int = Field(default=30, ge=1, le=100)


@router.post("/summary", response_model=ChatResponse)
async def summary(
    request: MailSummaryRequest, strategy: MailStrategyDep
) -> ChatResponse:
    result = await strategy.execute(request.model_dump())
    if isinstance(result, Success):
        return ChatResponse(
            ok=True,
            ui_type=result.ui_type,
            data=result.data,
            meta=result.meta or None,
        )
    assert isinstance(result, Error)
    return ChatResponse(
        ok=False,
        error=ChatErrorPayload(
            user_message=result.user_message,
            retry_after=result.retry_after,
        ),
    )


class AuthStatusResponse(BaseModel):
    connected: bool
    scopes: list[str] = []
    can_send: bool = False


@router.get("/auth-status", response_model=AuthStatusResponse)
async def auth_status(oauth: OAuthDep) -> AuthStatusResponse:
    """Lightweight check used by the frontend to decide whether to show
    the "Connect Google" prompt."""
    creds = None
    try:
        creds = oauth.credentials_for()
    except Exception as exc:  # noqa: BLE001
        logger.warning("auth-status check failed: %s", exc)
    if creds is None:
        return AuthStatusResponse(connected=False)
    granted = list(creds.scopes or [])
    return AuthStatusResponse(
        connected=True,
        scopes=granted,
        can_send=has_required_scopes(granted, GMAIL_SEND_SCOPES),
    )


# ---------- batch reply ----------


class DraftsRequest(BaseModel):
    message_ids: list[str] = Field(..., min_length=1, max_length=20)


class DraftPayload(BaseModel):
    message_id: str
    thread_id: str
    to: str
    subject: str
    body: str


class DraftsResponse(BaseModel):
    drafts: list[DraftPayload]
    failures: list[str] = []


@router.post("/drafts", response_model=DraftsResponse)
async def generate_drafts(
    request: DraftsRequest,
    oauth: OAuthDep,
    drafts: DraftDep,
    adapter_factory: AdapterFactoryDep,
) -> DraftsResponse:
    creds = oauth.credentials_for()
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google'a bağlı değilsin.",
        )
    adapter = adapter_factory(creds)

    out: list[DraftPayload] = []
    failures: list[str] = []
    for message_id in request.message_ids:
        try:
            payload = adapter.get_full_message(message_id)
        except GmailAdapterError as exc:
            logger.warning("Skipping %s: %s", message_id, exc)
            failures.append(message_id)
            continue
        body_text = _extract_body_text(payload)
        headers = {h["name"].lower(): h["value"] for h in payload.get("payload", {}).get("headers", [])}
        try:
            draft = await drafts.generate(
                message_id=message_id,
                thread_id=payload.get("threadId", ""),
                from_addr=headers.get("from", ""),
                subject=headers.get("subject", "(no subject)"),
                date=headers.get("date", ""),
                body_text=body_text,
            )
        except DraftGeneratorError as exc:
            logger.error("Draft failed for %s: %s", message_id, exc)
            failures.append(message_id)
            continue
        out.append(
            DraftPayload(
                message_id=draft.message_id,
                thread_id=draft.thread_id,
                to=draft.to,
                subject=draft.subject,
                body=draft.body,
            )
        )
    return DraftsResponse(drafts=out, failures=failures)


class SendRequest(BaseModel):
    message_id: str
    thread_id: str
    to: str
    subject: str
    body: str = Field(..., min_length=1, max_length=20000)


class SendResponse(BaseModel):
    sent_message_id: str | None = None
    error: ChatErrorPayload | None = None


@router.post("/send", response_model=SendResponse)
async def send_reply(
    request: SendRequest,
    oauth: OAuthDep,
    adapter_factory: AdapterFactoryDep,
) -> SendResponse:
    creds = oauth.credentials_for()
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google'a bağlı değilsin.",
        )
    if not has_required_scopes(creds.scopes or [], GMAIL_SEND_SCOPES):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "gmail.send izni yok. Tekrar bağlanıp gönderme iznini ver."
            ),
        )
    adapter = adapter_factory(creds)
    try:
        payload = adapter.send_reply(
            to=request.to,
            subject=request.subject,
            body=request.body,
            thread_id=request.thread_id,
            in_reply_to_message_id=request.message_id,
        )
    except GmailAdapterError as exc:
        logger.error("send failed: %s", exc)
        return SendResponse(
            error=ChatErrorPayload(user_message="Mail gönderilemedi.", retry_after=10)
        )
    return SendResponse(sent_message_id=payload.get("id"))


def _extract_body_text(payload: dict) -> str:
    """Best-effort body extraction.

    Walks the MIME tree and concatenates the first text/plain part(s).
    Falls back to the snippet if no plain-text part is present.
    """
    import base64

    def walk(part: dict) -> str:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data") or ""
            if data:
                try:
                    return base64.urlsafe_b64decode(data + "==").decode(
                        "utf-8", errors="replace"
                    )
                except Exception:  # noqa: BLE001
                    return ""
        chunks = []
        for child in part.get("parts", []) or []:
            text = walk(child)
            if text:
                chunks.append(text)
        return "\n".join(chunks)

    body = walk(payload.get("payload", {}))
    if body.strip():
        return body
    return payload.get("snippet", "")
