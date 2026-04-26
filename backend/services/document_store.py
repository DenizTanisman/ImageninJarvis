"""In-memory document registry.

Holds metadata about uploaded / Drive-fetched documents so the QA
strategy can look up a doc by id and pull text without re-uploading.
The actual file lives in the sandbox (``DocumentMeta.file_path``); the
parsed chunks are stored too so the strategy doesn't re-parse on every
question.

In-memory because Step 5 ships single-server dev only — a SQLite layer
can replace this without changing the public surface (``register`` /
``get`` / ``forget``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Literal


@dataclass(frozen=True)
class DocumentMeta:
    doc_id: str
    original_name: str
    mime_type: Literal["application/pdf", "text/plain"]
    page_count: int
    size_bytes: int
    file_path: str
    chunks: tuple[str, ...] = field(default_factory=tuple)


class DocumentStoreError(KeyError):
    pass


class DocumentStore:
    def __init__(self) -> None:
        self._items: dict[str, DocumentMeta] = {}
        self._lock = Lock()

    def register(self, meta: DocumentMeta) -> None:
        with self._lock:
            self._items[meta.doc_id] = meta

    def get(self, doc_id: str) -> DocumentMeta:
        with self._lock:
            try:
                return self._items[doc_id]
            except KeyError as exc:
                raise DocumentStoreError(f"unknown doc_id: {doc_id}") from exc

    def has(self, doc_id: str) -> bool:
        with self._lock:
            return doc_id in self._items

    def forget(self, doc_id: str) -> None:
        with self._lock:
            self._items.pop(doc_id, None)

    def attach_chunks(self, doc_id: str, chunks: tuple[str, ...]) -> None:
        with self._lock:
            existing = self._items.get(doc_id)
            if existing is None:
                raise DocumentStoreError(f"unknown doc_id: {doc_id}")
            self._items[doc_id] = DocumentMeta(
                doc_id=existing.doc_id,
                original_name=existing.original_name,
                mime_type=existing.mime_type,
                page_count=existing.page_count,
                size_bytes=existing.size_bytes,
                file_path=existing.file_path,
                chunks=chunks,
            )
