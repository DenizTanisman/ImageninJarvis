"""Document Q&A route.

POST /document — single ``action: "ask"`` for now. Future actions (e.g.
"summarize", "translate") plug into the same dispatch table.
"""
from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies import get_document_strategy
from app.schemas import ChatErrorPayload, ChatResponse
from capabilities.document.strategy import DocumentStrategy
from core.result import Error, Success

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/document", tags=["document"])

DocumentStrategyDep = Annotated[DocumentStrategy, Depends(get_document_strategy)]


class DocumentAskRequest(BaseModel):
    action: Literal["ask"] = "ask"
    doc_id: str = Field(..., min_length=1, max_length=64)
    question: str = Field(..., min_length=1, max_length=2000)


@router.post("", response_model=ChatResponse)
async def document(
    request: DocumentAskRequest, strategy: DocumentStrategyDep
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
