"""Document upload route.

POST /upload accepts a single PDF or text/plain file and hands it to
the shared ingest pipeline (``capabilities.document.ingest``), which
applies the same MIME / size defenses as the Drive import path.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.dependencies import get_document_store, get_sandbox_root
from capabilities.document.ingest import MAX_BYTES, IngestError, ingest_bytes
from services.document_store import DocumentStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["document"])

DocumentStoreDep = Annotated[DocumentStore, Depends(get_document_store)]
SandboxDep = Annotated[Path, Depends(get_sandbox_root)]


class UploadResponse(BaseModel):
    doc_id: str
    page_count: int
    original_name: str
    mime_type: str
    size_bytes: int


@router.post("", response_model=UploadResponse)
async def upload(
    store: DocumentStoreDep,
    sandbox_root: SandboxDep,
    file: Annotated[UploadFile, File(...)],
) -> UploadResponse:
    raw = await _read_capped(file)
    try:
        meta = ingest_bytes(
            raw=raw,
            original_name=file.filename or "document",
            store=store,
            sandbox_root=sandbox_root,
        )
    except IngestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.user_message) from exc
    return UploadResponse(
        doc_id=meta.doc_id,
        page_count=meta.page_count,
        original_name=meta.original_name,
        mime_type=meta.mime_type,
        size_bytes=meta.size_bytes,
    )


async def _read_capped(file: UploadFile) -> bytes:
    """Stream the upload into memory but bail past the size cap."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Dosya 10 MB sınırını aşıyor ({total} bayt).",
            )
        chunks.append(chunk)
    return b"".join(chunks)
