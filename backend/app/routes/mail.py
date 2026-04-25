"""POST /mail/summary — direct shortcut entry point.

Frontend calls this when the user clicks the Mail shortcut. Body carries
the active range; the dispatched strategy (MailStrategy) returns either
a Success(data=...) which we forward, or an Error with a user-facing
message.
"""
from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies import get_mail_strategy, get_oauth_service
from app.schemas import ChatErrorPayload, ChatResponse
from capabilities.gmail.strategy import MailStrategy
from core.result import Error, Success
from services.auth_oauth import GoogleOAuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mail", tags=["mail"])

MailStrategyDep = Annotated[MailStrategy, Depends(get_mail_strategy)]
OAuthDep = Annotated[GoogleOAuthService, Depends(get_oauth_service)]


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
    return AuthStatusResponse(connected=True, scopes=list(creds.scopes or []))
