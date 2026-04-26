"""DocumentStrategy — Q&A over an uploaded / Drive-fetched document.

MVP retrieval is naive: first ``MAX_CHUNKS`` chunks of the doc go into
the prompt. The chunk window in 5.4 already keeps each chunk ≤ 8000
chars, so 3 chunks fits Gemini 2.5 Flash with budget for the question
+ answer. A future iteration can swap this for embedding-based
retrieval without touching the strategy's contract.
"""
from __future__ import annotations

import logging
from typing import Any

from core.base_strategy import CapabilityStrategy
from core.result import Error, Result, Success
from services.document_store import DocumentStore, DocumentStoreError
from services.gemini_client import GeminiClient, GeminiUnavailable

from .prompts import DOCUMENT_QA_SYSTEM_PROMPT, build_document_user_message

logger = logging.getLogger(__name__)

MAX_CHUNKS = 3
MAX_QUESTION_CHARS = 2000


class DocumentStrategy(CapabilityStrategy):
    name = "document"
    intent_keys = ("document", "doc", "belge")

    def __init__(
        self,
        *,
        store: DocumentStore,
        gemini: GeminiClient,
    ) -> None:
        self._store = store
        self._gemini = gemini

    def can_handle(self, intent: dict[str, Any]) -> bool:
        return intent.get("type") == "document"

    async def execute(self, payload: dict[str, Any]) -> Result:
        action = payload.get("action") or "ask"
        if action != "ask":
            return Error(
                message=f"unknown action: {action!r}",
                user_message="Bu döküman isteğini anlayamadım.",
                user_notify=True,
                log_level="info",
            )
        doc_id = (payload.get("doc_id") or "").strip()
        question = (payload.get("question") or "").strip()
        if not doc_id:
            return Error(
                message="missing doc_id",
                user_message="Hangi belge hakkında soruyorsun?",
                user_notify=True,
                log_level="info",
            )
        if not question:
            return Error(
                message="empty question",
                user_message="Sorunu yazmamışsın.",
                user_notify=True,
                log_level="info",
            )
        if len(question) > MAX_QUESTION_CHARS:
            return Error(
                message="question too long",
                user_message=f"Soru en fazla {MAX_QUESTION_CHARS} karakter olabilir.",
                user_notify=True,
                log_level="info",
            )

        try:
            meta = self._store.get(doc_id)
        except DocumentStoreError:
            return Error(
                message="unknown doc_id",
                user_message="Bu belge artık sistemde yok, tekrar yükle.",
                user_notify=True,
                log_level="info",
            )
        if not meta.chunks:
            return Error(
                message="no chunks",
                user_message="Belgenin içeriği boş çıktı, başka bir dosya dene.",
                user_notify=True,
                log_level="info",
            )

        prompt = build_document_user_message(
            question=question, chunks=meta.chunks[:MAX_CHUNKS]
        )
        try:
            answer = await self._gemini.generate_text(
                prompt, system=DOCUMENT_QA_SYSTEM_PROMPT
            )
        except GeminiUnavailable as exc:
            logger.error("Document QA Gemini call failed: %s", exc)
            return Error(
                message=str(exc),
                user_message="Belge cevabı üretilemedi, biraz sonra tekrar dene.",
                retry_after=15,
            )

        return Success(
            data={
                "doc_id": doc_id,
                "question": question,
                "answer": answer.strip(),
                "chunks_used": min(len(meta.chunks), MAX_CHUNKS),
                "total_chunks": len(meta.chunks),
            },
            ui_type="DocumentAnswer",
        )

    def render_hint(self) -> str:
        return "DocumentAnswer"
