"""Document upload route.

POST /upload accepts a single PDF or text/plain file, validates the
content (not just the declared mime), drops it in a per-upload sandbox
folder, and registers metadata with the in-process DocumentStore.

Security defenses (CLAUDE.md §4.4):
- MIME validated by sniffing the binary header (PDF: ``%PDF-``; TXT:
  must decode as UTF-8 / Latin-1) — extension is ignored entirely.
- Hard 10 MB cap; the upstream client sees a friendly 413 / 422 instead
  of an OOM-able stream.
- Sandbox path is ``$JARVIS_SANDBOX_DIR/<uuid>/<safe-name>``; the uuid
  isolates concurrent uploads, the safe-name strips path traversal.
- The chunk pipeline (Step 5.4) runs synchronously after registration
  so a malformed PDF surfaces here, not on the first Q&A round-trip.
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from io import BytesIO
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.dependencies import get_document_store, get_sandbox_root
from services.document_store import DocumentMeta, DocumentStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["document"])

DocumentStoreDep = Annotated[DocumentStore, Depends(get_document_store)]
SandboxDep = Annotated[Path, Depends(get_sandbox_root)]

MAX_BYTES = 10 * 1024 * 1024  # 10 MB
PDF_MAGIC = b"%PDF-"
SUPPORTED_MIMES: tuple[str, ...] = ("application/pdf", "text/plain")
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


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
    mime = _detect_mime(raw)
    if mime is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Sadece PDF veya düz metin dosyası kabul ediliyor.",
        )

    page_count = _count_pages(raw, mime)

    doc_id = uuid.uuid4().hex
    safe_name = _sanitize_filename(file.filename or "document")
    target_dir = sandbox_root / doc_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / safe_name
    target_path.write_bytes(raw)

    meta = DocumentMeta(
        doc_id=doc_id,
        original_name=safe_name,
        mime_type=mime,  # type: ignore[arg-type]
        page_count=page_count,
        size_bytes=len(raw),
        file_path=str(target_path),
    )
    store.register(meta)
    logger.info(
        "Document uploaded doc_id=%s name=%s mime=%s pages=%d size=%d",
        doc_id, safe_name, mime, page_count, len(raw),
    )
    return UploadResponse(
        doc_id=doc_id,
        page_count=page_count,
        original_name=safe_name,
        mime_type=mime,
        size_bytes=len(raw),
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
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Dosya 10 MB sınırını aşıyor ({total} bayt).",
            )
        chunks.append(chunk)
    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Boş dosya gönderildi.",
        )
    return b"".join(chunks)


def _detect_mime(raw: bytes) -> str | None:
    """Sniff the binary header. PDFs always start with %PDF-; TXT just
    needs to decode cleanly as UTF-8 (or Latin-1 as a fallback)."""
    if raw.startswith(PDF_MAGIC):
        return "application/pdf"
    try:
        raw.decode("utf-8")
        return "text/plain"
    except UnicodeDecodeError:
        pass
    try:
        raw.decode("latin-1")
        # Latin-1 always decodes; only accept if it contains no NULs and
        # the printable ratio is high — keeps random binaries out.
        if b"\x00" not in raw and _is_mostly_printable(raw):
            return "text/plain"
    except UnicodeDecodeError:
        pass
    return None


def _is_mostly_printable(raw: bytes) -> bool:
    if not raw:
        return False
    printable = sum(
        1 for b in raw if b in (9, 10, 13) or 32 <= b <= 126 or b >= 0xA0
    )
    return printable / len(raw) > 0.95


def _count_pages(raw: bytes, mime: str) -> int:
    if mime == "application/pdf":
        try:
            reader = PdfReader(BytesIO(raw))
            return len(reader.pages)
        except PdfReadError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"PDF okunamadı: {exc}",
            ) from exc
    return 1  # plain text counts as a single "page"


def _sanitize_filename(name: str) -> str:
    """Strip any path components and collapse unsafe chars. Avoids
    directory-traversal payloads like ``../../etc/passwd``."""
    base = os.path.basename(name).strip()
    if not base:
        base = "document"
    safe = SAFE_NAME.sub("_", base)
    return safe[:200] or "document"
