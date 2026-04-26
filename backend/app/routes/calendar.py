"""Calendar HTTP route.

Single ``POST /calendar`` endpoint that dispatches on ``payload.action``.
Mirrors how /mail and /translation hand a typed payload to the strategy
and forward Result → ChatResponse. The frontend sends one of:

  {"action": "list", "days": 7}
  {"action": "create", "summary": "...", "start": "<iso>", "end": "<iso>",
   "description": ""}
  {"action": "update", "event_id": "...", ...optional fields...}
  {"action": "delete", "event_id": "..."}

Delete confirmation lives in the UI (Step 4.7) — by the time the request
hits this route the user has already accepted the modal.
"""
from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies import get_calendar_strategy
from app.schemas import ChatErrorPayload, ChatResponse
from capabilities.calendar.strategy import CalendarStrategy
from core.result import Error, Success

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"])

CalendarStrategyDep = Annotated[CalendarStrategy, Depends(get_calendar_strategy)]


class CalendarRequest(BaseModel):
    action: Literal["list", "create", "update", "delete"]
    days: int | None = Field(default=None, ge=1, le=60)
    event_id: str | None = None
    summary: str | None = Field(default=None, max_length=300)
    start: str | None = None
    end: str | None = None
    description: str | None = Field(default=None, max_length=4000)


@router.post("", response_model=ChatResponse)
async def calendar(
    request: CalendarRequest, strategy: CalendarStrategyDep
) -> ChatResponse:
    payload: dict[str, Any] = {
        k: v for k, v in request.model_dump().items() if v is not None
    }
    result = await strategy.execute(payload)
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
