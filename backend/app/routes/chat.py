"""POST /chat — main entry point for both chat and voice text inputs."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_dispatcher
from app.schemas import ChatErrorPayload, ChatRequest, ChatResponse
from core.dispatcher import Dispatcher
from core.result import Error, Success

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

DispatcherDep = Annotated[Dispatcher, Depends(get_dispatcher)]


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, dispatcher: DispatcherDep) -> ChatResponse:
    result = await dispatcher.handle(request.text)
    if isinstance(result, Success):
        return ChatResponse(
            ok=True,
            ui_type=result.ui_type,
            data=result.data,
            meta=result.meta or None,
        )
    assert isinstance(result, Error)
    if result.user_notify:
        logger.log(
            _level_for(result.log_level),
            "chat dispatcher error: %s",
            result.message,
        )
    return ChatResponse(
        ok=False,
        error=ChatErrorPayload(
            user_message=result.user_message,
            retry_after=result.retry_after,
        ),
    )


def _level_for(name: str) -> int:
    return {"info": logging.INFO, "warning": logging.WARNING, "error": logging.ERROR}.get(
        name, logging.ERROR
    )
