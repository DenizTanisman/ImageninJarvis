"""Public request / response schemas exposed by the FastAPI app."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


class ChatErrorPayload(BaseModel):
    user_message: str
    retry_after: int | None = None


class ChatResponse(BaseModel):
    ok: bool
    ui_type: str | None = None
    data: Any = None
    meta: dict[str, Any] | None = None
    error: ChatErrorPayload | None = None
