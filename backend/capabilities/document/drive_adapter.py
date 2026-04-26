"""Google Drive v3 wrapper.

Mirrors the GmailAdapter / CalendarAdapter contract: pre-built
``Credentials`` go in, ``DriveFile`` dataclasses come out. Only PDF and
plain-text files are surfaced — Step 5 hands those to the parser; other
formats stay out of the picker so the user can't pick something we can't
ingest.
"""
from __future__ import annotations

import io
import logging
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from .models import DriveFile

logger = logging.getLogger(__name__)

EXECUTE_NUM_RETRIES = 3
DEFAULT_PAGE_SIZE = 50
SUPPORTED_MIME_TYPES: tuple[str, ...] = ("application/pdf", "text/plain")
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024  # match upload route's 10 MB cap


class DriveAdapterError(RuntimeError):
    pass


class DriveAdapter:
    """Thin synchronous wrapper around Drive v3."""

    def __init__(self, credentials: Credentials, *, service: Any | None = None) -> None:
        if service is not None:
            self._service = service
        else:
            self._service = build(
                "drive", "v3", credentials=credentials, cache_discovery=False
            )

    def list_files(
        self,
        *,
        mime_types: tuple[str, ...] = SUPPORTED_MIME_TYPES,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> list[DriveFile]:
        """Return non-trashed PDF / TXT files the user owns or has access to.

        We OR the mime types in the search query so a single request covers
        both formats; fields are clamped to the columns the picker renders
        plus mimeType (so the route can reject anything unexpected later)."""
        if not mime_types:
            return []
        clauses = " or ".join(f"mimeType='{mt}'" for mt in mime_types)
        query = f"({clauses}) and trashed=false"
        try:
            response = (
                self._service.files()
                .list(
                    q=query,
                    pageSize=page_size,
                    fields="files(id,name,mimeType,size,modifiedTime)",
                    orderBy="modifiedTime desc",
                )
                .execute(num_retries=EXECUTE_NUM_RETRIES)
            )
        except (HttpError, OSError) as exc:
            raise DriveAdapterError(f"Drive list failed: {exc}") from exc

        out: list[DriveFile] = []
        for raw in response.get("files", []):
            parsed = _parse_file(raw)
            if parsed is not None:
                out.append(parsed)
        return out

    def download_file(self, file_id: str, *, max_bytes: int = MAX_DOWNLOAD_BYTES) -> bytes:
        """Stream the file content to memory, refusing payloads larger than
        ``max_bytes`` so a malicious / accidentally-huge Drive entry can't
        balloon the server's memory or fill the sandbox disk."""
        if not file_id:
            raise DriveAdapterError("download_file requires a file_id")
        try:
            request = self._service.files().get_media(fileId=file_id)
        except (HttpError, OSError) as exc:
            raise DriveAdapterError(f"Drive download init failed: {exc}") from exc

        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        try:
            done = False
            while not done:
                _status, done = downloader.next_chunk(num_retries=EXECUTE_NUM_RETRIES)
                if buffer.tell() > max_bytes:
                    raise DriveAdapterError(
                        f"Drive file exceeds {max_bytes} byte cap"
                    )
        except (HttpError, OSError) as exc:
            raise DriveAdapterError(f"Drive download failed: {exc}") from exc
        return buffer.getvalue()


def _parse_file(raw: dict[str, Any]) -> DriveFile | None:
    file_id = raw.get("id")
    name = raw.get("name")
    mime_type = raw.get("mimeType")
    if not isinstance(file_id, str) or not isinstance(name, str) or not isinstance(mime_type, str):
        return None
    if mime_type not in SUPPORTED_MIME_TYPES:
        return None
    size_raw = raw.get("size")
    try:
        size = int(size_raw) if size_raw is not None else 0
    except (TypeError, ValueError):
        size = 0
    return DriveFile(
        id=file_id,
        name=name,
        mime_type=mime_type,
        size_bytes=size,
        modified_time=raw.get("modifiedTime") or "",
    )
