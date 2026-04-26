"""Translation HTTP route.

POST /translation — direct shortcut entry point. Bypasses the classifier
the same way /mail/summary does because the UI already knows the user's
intent (and the source/target lang). Chat path uses the classifier and
hits the same TranslationStrategy through the dispatcher.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies import get_translation_strategy
from app.schemas import ChatErrorPayload, ChatResponse
from capabilities.translation.strategy import TranslationStrategy
from core.result import Error, Success

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/translation", tags=["translation"])

TranslationStrategyDep = Annotated[TranslationStrategy, Depends(get_translation_strategy)]


class TranslationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)
    source: str = Field(default="auto", min_length=2, max_length=10)
    target: str = Field(..., min_length=2, max_length=10)


@router.post("", response_model=ChatResponse)
async def translate(
    request: TranslationRequest, strategy: TranslationStrategyDep
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
