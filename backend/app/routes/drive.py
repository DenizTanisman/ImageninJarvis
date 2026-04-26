"""Google Drive picker + import routes.

GET  /drive/files       — list the user's PDF / TXT files (Step 5.6 picker)
POST /drive/import      — pull a file by id, validate + sandbox + parse it,
                          and register it the same way /upload does.

The user must have already granted ``drive.readonly`` (Step 5.1). Both
routes return 401 if no creds, 403 if the scope is missing.
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies import (
    get_document_store,
    get_drive_adapter_factory,
    get_oauth_service,
    get_sandbox_root,
)
from capabilities.document.drive_adapter import DriveAdapterError
from capabilities.document.ingest import IngestError, ingest_bytes
from services.auth_oauth import (
    DRIVE_SCOPES,
    GoogleOAuthService,
    has_required_scopes,
)
from services.document_store import DocumentStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/drive", tags=["document"])

OAuthDep = Annotated[GoogleOAuthService, Depends(get_oauth_service)]
AdapterFactoryDep = Annotated[object, Depends(get_drive_adapter_factory)]
DocumentStoreDep = Annotated[DocumentStore, Depends(get_document_store)]
SandboxDep = Annotated[Path, Depends(get_sandbox_root)]


class DriveFileEntry(BaseModel):
    id: str
    name: str
    mime_type: str
    size_bytes: int
    modified_time: str


class DriveListResponse(BaseModel):
    files: list[DriveFileEntry]


class DriveImportRequest(BaseModel):
    file_id: str = Field(..., min_length=1, max_length=200)


class DriveImportResponse(BaseModel):
    doc_id: str
    page_count: int
    original_name: str
    mime_type: str
    size_bytes: int


def _ensure_drive_credentials(oauth: GoogleOAuthService):
    creds = oauth.credentials_for()
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google'a bağlı değilsin.",
        )
    if not has_required_scopes(creds.scopes or [], DRIVE_SCOPES):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Drive izni yok. Tekrar bağlanıp Drive iznini ver.",
        )
    return creds


@router.get("/files", response_model=DriveListResponse)
async def list_files(
    oauth: OAuthDep, adapter_factory: AdapterFactoryDep
) -> DriveListResponse:
    creds = _ensure_drive_credentials(oauth)
    adapter = adapter_factory(creds)
    try:
        files = adapter.list_files()
    except DriveAdapterError as exc:
        logger.error("Drive list failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Drive listesi alınamadı.",
        ) from exc
    return DriveListResponse(
        files=[DriveFileEntry(**_serialise(f)) for f in files]
    )


@router.post("/import", response_model=DriveImportResponse)
async def import_file(
    request: DriveImportRequest,
    oauth: OAuthDep,
    adapter_factory: AdapterFactoryDep,
    store: DocumentStoreDep,
    sandbox_root: SandboxDep,
) -> DriveImportResponse:
    creds = _ensure_drive_credentials(oauth)
    adapter = adapter_factory(creds)

    # Find the file in the user's PDF / TXT list to recover the original
    # name. Drive API can return name via files.get too, but listing is
    # already filtered to the safe MIME set so we reuse it.
    try:
        files = adapter.list_files()
    except DriveAdapterError as exc:
        logger.error("Drive list failed during import: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Drive listesi alınamadı.",
        ) from exc
    match = next((f for f in files if f.id == request.file_id), None)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bu dosya Drive'da görünmüyor (veya desteklenmeyen tip).",
        )

    try:
        raw = adapter.download_file(request.file_id)
    except DriveAdapterError as exc:
        logger.error("Drive download failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Drive dosyası indirilemedi.",
        ) from exc

    try:
        meta = ingest_bytes(
            raw=raw,
            original_name=match.name,
            store=store,
            sandbox_root=sandbox_root,
        )
    except IngestError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail=exc.user_message
        ) from exc

    return DriveImportResponse(
        doc_id=meta.doc_id,
        page_count=meta.page_count,
        original_name=meta.original_name,
        mime_type=meta.mime_type,
        size_bytes=meta.size_bytes,
    )


def _serialise(file_obj) -> dict:
    data = asdict(file_obj)
    return data
