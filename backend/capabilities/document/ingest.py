"""Shared ingestion pipeline.

Both ``/upload`` (browser drag-drop) and ``/drive/import`` (Drive picker)
end up doing the same work: validate the bytes, drop them in a
per-doc sandbox folder, parse + chunk, and register everything in the
DocumentStore. Centralising here keeps the route layer thin and makes
sure both entry points apply the same MIME / size defenses.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import time
import uuid
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from services.document_store import DocumentMeta, DocumentStore

from .parser import DocumentParseError, parse_and_chunk

DEFAULT_MAX_AGE_SECONDS = 24 * 60 * 60  # 24 hours

logger = logging.getLogger(__name__)

MAX_BYTES = 10 * 1024 * 1024  # 10 MB
PDF_MAGIC = b"%PDF-"
SUPPORTED_MIMES: tuple[str, ...] = ("application/pdf", "text/plain")
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class IngestError(Exception):
    """Raised when ingestion fails. ``status_code`` mirrors the HTTP code
    the route layer should surface; ``user_message`` is sanitized."""

    def __init__(self, status_code: int, user_message: str) -> None:
        super().__init__(user_message)
        self.status_code = status_code
        self.user_message = user_message


def ingest_bytes(
    *,
    raw: bytes,
    original_name: str,
    store: DocumentStore,
    sandbox_root: Path,
) -> DocumentMeta:
    if len(raw) == 0:
        raise IngestError(400, "Boş dosya gönderildi.")
    if len(raw) > MAX_BYTES:
        raise IngestError(
            413, f"Dosya 10 MB sınırını aşıyor ({len(raw)} bayt)."
        )

    mime = detect_mime(raw)
    if mime is None:
        raise IngestError(
            415, "Sadece PDF veya düz metin dosyası kabul ediliyor."
        )

    page_count = _count_pages(raw, mime)

    doc_id = uuid.uuid4().hex
    safe_name = sanitize_filename(original_name)
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
    try:
        try:
            chunks = parse_and_chunk(file_path=target_path, mime_type=mime)
        except DocumentParseError as exc:
            store.forget(doc_id)
            raise IngestError(422, str(exc)) from exc
        store.attach_chunks(doc_id, chunks)
    finally:
        # Sandbox file is no longer needed once chunks live in the
        # DocumentStore; deleting eagerly closes the §4.4 attack window
        # where a malicious upload sits on disk between requests.
        cleanup_sandbox(target_dir)

    logger.info(
        "Document ingested doc_id=%s name=%s mime=%s pages=%d size=%d chunks=%d",
        doc_id, safe_name, mime, page_count, len(raw), len(chunks),
    )
    return store.get(doc_id)


def cleanup_sandbox(path: Path) -> None:
    """Best-effort recursive delete. Never raises — a failed cleanup
    must not break the user-visible ingest result."""
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Sandbox cleanup failed for %s: %s", path, exc)


def sweep_old_sandboxes(
    root: Path, *, max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS
) -> int:
    """Remove sandbox subdirectories whose mtime is older than the cap.

    Belt-and-suspenders for cases where ``cleanup_sandbox`` didn't run
    (process crash mid-ingest, OS killed the worker, etc.). Returns the
    number of directories removed so the caller can log it."""
    if not root.exists():
        return 0
    cutoff = time.time() - max_age_seconds
    removed = 0
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        try:
            if entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry, ignore_errors=True)
                removed += 1
        except OSError as exc:
            logger.warning("Sweep failed for %s: %s", entry, exc)
    return removed


def detect_mime(raw: bytes) -> str | None:
    if raw.startswith(PDF_MAGIC):
        return "application/pdf"
    try:
        raw.decode("utf-8")
        return "text/plain"
    except UnicodeDecodeError:
        pass
    try:
        raw.decode("latin-1")
        if b"\x00" not in raw and _is_mostly_printable(raw):
            return "text/plain"
    except UnicodeDecodeError:
        pass
    return None


def sanitize_filename(name: str) -> str:
    base = os.path.basename(name).strip()
    if not base:
        base = "document"
    safe = SAFE_NAME.sub("_", base)
    return safe[:200] or "document"


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
            raise IngestError(422, f"PDF okunamadı: {exc}") from exc
    return 1
