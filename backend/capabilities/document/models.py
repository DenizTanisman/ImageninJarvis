from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DriveFile:
    """Plain-data view of a Google Drive file we can ingest.

    Only the fields the frontend picker needs to render a row, plus the
    mime type so the backend can re-validate that the file is one we
    actually parse (PDF / TXT)."""

    id: str
    name: str
    mime_type: str
    size_bytes: int
    modified_time: str
