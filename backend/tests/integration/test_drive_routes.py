from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import (
    get_document_store,
    get_drive_adapter_factory,
    get_oauth_service,
    get_sandbox_root,
)
from app.main import app
from capabilities.document.drive_adapter import DriveAdapterError
from capabilities.document.models import DriveFile
from services.document_store import DocumentStore


@pytest.fixture()
def store() -> DocumentStore:
    return DocumentStore()


@pytest.fixture()
def client(tmp_path: Path, store: DocumentStore) -> TestClient:
    app.dependency_overrides[get_document_store] = lambda: store
    app.dependency_overrides[get_sandbox_root] = lambda: tmp_path
    yield TestClient(app)
    app.dependency_overrides.clear()


def _override_oauth(*, has_drive_scope: bool = True) -> MagicMock:
    fake = MagicMock()
    if has_drive_scope:
        fake.credentials_for.return_value = MagicMock(
            scopes=[
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ]
        )
    else:
        fake.credentials_for.return_value = MagicMock(
            scopes=["https://www.googleapis.com/auth/gmail.readonly"]
        )
    app.dependency_overrides[get_oauth_service] = lambda: fake
    return fake


def _override_oauth_disconnected() -> None:
    fake = MagicMock()
    fake.credentials_for.return_value = None
    app.dependency_overrides[get_oauth_service] = lambda: fake


def _override_adapter(adapter: MagicMock) -> None:
    app.dependency_overrides[get_drive_adapter_factory] = lambda: (lambda creds: adapter)


# ---------- list ----------


def test_drive_list_returns_files(client: TestClient) -> None:
    _override_oauth()
    adapter = MagicMock()
    adapter.list_files.return_value = [
        DriveFile(
            id="f1",
            name="plan.pdf",
            mime_type="application/pdf",
            size_bytes=1234,
            modified_time="2026-04-25T10:00:00Z",
        ),
        DriveFile(
            id="f2",
            name="notes.txt",
            mime_type="text/plain",
            size_bytes=10,
            modified_time="2026-04-24T10:00:00Z",
        ),
    ]
    _override_adapter(adapter)
    response = client.get("/drive/files")
    assert response.status_code == 200
    body = response.json()
    assert len(body["files"]) == 2
    assert body["files"][0]["id"] == "f1"
    assert body["files"][0]["mime_type"] == "application/pdf"


def test_drive_list_returns_401_when_disconnected(client: TestClient) -> None:
    _override_oauth_disconnected()
    _override_adapter(MagicMock())
    response = client.get("/drive/files")
    assert response.status_code == 401


def test_drive_list_returns_403_when_drive_scope_missing(client: TestClient) -> None:
    _override_oauth(has_drive_scope=False)
    _override_adapter(MagicMock())
    response = client.get("/drive/files")
    assert response.status_code == 403


def test_drive_list_returns_502_when_adapter_fails(client: TestClient) -> None:
    _override_oauth()
    adapter = MagicMock()
    adapter.list_files.side_effect = DriveAdapterError("offline")
    _override_adapter(adapter)
    response = client.get("/drive/files")
    assert response.status_code == 502


# ---------- import ----------


def test_drive_import_ingests_txt_file(
    client: TestClient, store: DocumentStore
) -> None:
    _override_oauth()
    adapter = MagicMock()
    adapter.list_files.return_value = [
        DriveFile(
            id="f1",
            name="notes.txt",
            mime_type="text/plain",
            size_bytes=10,
            modified_time="2026-04-25T10:00:00Z",
        )
    ]
    adapter.download_file.return_value = b"Bu bir test belgesidir.\n" * 100
    _override_adapter(adapter)
    response = client.post("/drive/import", json={"file_id": "f1"})
    assert response.status_code == 200
    body = response.json()
    assert body["mime_type"] == "text/plain"
    assert body["original_name"] == "notes.txt"
    assert store.has(body["doc_id"])


def test_drive_import_returns_404_for_unknown_file(client: TestClient) -> None:
    _override_oauth()
    adapter = MagicMock()
    adapter.list_files.return_value = []  # nothing matches
    _override_adapter(adapter)
    response = client.post("/drive/import", json={"file_id": "missing"})
    assert response.status_code == 404


def test_drive_import_returns_502_when_download_fails(client: TestClient) -> None:
    _override_oauth()
    adapter = MagicMock()
    adapter.list_files.return_value = [
        DriveFile(
            id="f1",
            name="x.pdf",
            mime_type="application/pdf",
            size_bytes=1,
            modified_time="",
        )
    ]
    adapter.download_file.side_effect = DriveAdapterError("offline")
    _override_adapter(adapter)
    response = client.post("/drive/import", json={"file_id": "f1"})
    assert response.status_code == 502


def test_drive_import_returns_415_when_downloaded_bytes_arent_pdf_or_txt(
    client: TestClient,
) -> None:
    _override_oauth()
    adapter = MagicMock()
    adapter.list_files.return_value = [
        DriveFile(
            id="f1",
            name="logo.pdf",
            mime_type="application/pdf",
            size_bytes=1,
            modified_time="",
        )
    ]
    # Download returns PNG bytes despite the listed mime type.
    adapter.download_file.return_value = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    _override_adapter(adapter)
    response = client.post("/drive/import", json={"file_id": "f1"})
    assert response.status_code == 415


def test_drive_import_returns_403_when_drive_scope_missing(client: TestClient) -> None:
    _override_oauth(has_drive_scope=False)
    _override_adapter(MagicMock())
    response = client.post("/drive/import", json={"file_id": "f1"})
    assert response.status_code == 403
