import ssl
from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError

from capabilities.document.drive_adapter import (
    MAX_DOWNLOAD_BYTES,
    DriveAdapter,
    DriveAdapterError,
)
from capabilities.document.models import DriveFile


def _adapter(service: MagicMock | None = None) -> tuple[DriveAdapter, MagicMock]:
    svc = service or MagicMock()
    return DriveAdapter(credentials=MagicMock(), service=svc), svc


def _file_payload(
    *,
    file_id: str = "f1",
    name: str = "Q2 plan.pdf",
    mime_type: str = "application/pdf",
    size: str | None = "12345",
    modified: str = "2026-04-25T10:00:00Z",
) -> dict:
    payload = {
        "id": file_id,
        "name": name,
        "mimeType": mime_type,
        "modifiedTime": modified,
    }
    if size is not None:
        payload["size"] = size
    return payload


# ---------- list ----------


def test_list_files_returns_only_supported_mime_types() -> None:
    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = {
        "files": [
            _file_payload(file_id="f1", mime_type="application/pdf"),
            _file_payload(file_id="f2", name="notes.txt", mime_type="text/plain"),
            _file_payload(file_id="f3", name="logo.png", mime_type="image/png"),
        ]
    }
    adapter, _ = _adapter(service)
    files = adapter.list_files()
    assert {f.id for f in files} == {"f1", "f2"}
    assert all(isinstance(f, DriveFile) for f in files)


def test_list_files_query_or_combines_mime_types_and_excludes_trashed() -> None:
    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = {"files": []}
    adapter, _ = _adapter(service)
    adapter.list_files()
    kwargs = service.files.return_value.list.call_args.kwargs
    assert (
        kwargs["q"]
        == "(mimeType='application/pdf' or mimeType='text/plain') and trashed=false"
    )
    assert kwargs["fields"] == "files(id,name,mimeType,size,modifiedTime)"
    assert kwargs["orderBy"] == "modifiedTime desc"


def test_list_files_returns_empty_when_no_mime_types() -> None:
    adapter, _ = _adapter()
    assert adapter.list_files(mime_types=()) == []


def test_list_files_skips_payloads_with_unsupported_mime_or_missing_id() -> None:
    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = {
        "files": [
            {"id": "f1", "name": "x"},  # missing mimeType
            _file_payload(file_id="f2", mime_type="application/zip"),
            _file_payload(file_id="f3"),
        ]
    }
    adapter, _ = _adapter(service)
    files = adapter.list_files()
    assert [f.id for f in files] == ["f3"]


def test_list_files_handles_missing_size_field() -> None:
    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = {
        "files": [_file_payload(file_id="f1", size=None)]
    }
    adapter, _ = _adapter(service)
    files = adapter.list_files()
    assert files[0].size_bytes == 0


def test_list_files_wraps_http_error() -> None:
    service = MagicMock()
    service.files.return_value.list.return_value.execute.side_effect = HttpError(
        MagicMock(status=403), b"forbidden"
    )
    adapter, _ = _adapter(service)
    with pytest.raises(DriveAdapterError):
        adapter.list_files()


def test_list_files_wraps_ssl_error() -> None:
    service = MagicMock()
    service.files.return_value.list.return_value.execute.side_effect = ssl.SSLEOFError(
        "EOF"
    )
    adapter, _ = _adapter(service)
    with pytest.raises(DriveAdapterError):
        adapter.list_files()


# ---------- download ----------


def _make_downloader_chain(chunks: list[bytes]):
    """Return a fake MediaIoBaseDownload that streams ``chunks`` into the
    target buffer when ``next_chunk`` is called."""

    class _FakeDownloader:
        def __init__(self, fd, _request):
            self._fd = fd
            self._chunks = list(chunks)

        def next_chunk(self, num_retries: int = 0):
            if self._chunks:
                self._fd.write(self._chunks.pop(0))
                return (None, len(self._chunks) == 0)
            return (None, True)

    return _FakeDownloader


def test_download_file_streams_bytes() -> None:
    service = MagicMock()
    adapter, _ = _adapter(service)
    fake_dl = _make_downloader_chain([b"hello ", b"world"])
    with patch("capabilities.document.drive_adapter.MediaIoBaseDownload", fake_dl):
        result = adapter.download_file("f1")
    assert result == b"hello world"


def test_download_file_rejects_empty_id() -> None:
    adapter, _ = _adapter()
    with pytest.raises(DriveAdapterError):
        adapter.download_file("")


def test_download_file_rejects_oversize_payload() -> None:
    """Stream produces more bytes than the cap → adapter aborts so a
    malicious Drive file can't OOM the server."""
    big = b"x" * (MAX_DOWNLOAD_BYTES + 1)
    fake_dl = _make_downloader_chain([big])
    service = MagicMock()
    adapter, _ = _adapter(service)
    with patch("capabilities.document.drive_adapter.MediaIoBaseDownload", fake_dl):
        with pytest.raises(DriveAdapterError):
            adapter.download_file("f1")


def test_download_file_wraps_http_error_during_get_media() -> None:
    service = MagicMock()
    service.files.return_value.get_media.side_effect = HttpError(
        MagicMock(status=404), b"not found"
    )
    adapter, _ = _adapter(service)
    with pytest.raises(DriveAdapterError):
        adapter.download_file("f1")


def test_download_file_wraps_http_error_during_chunk() -> None:
    service = MagicMock()
    adapter, _ = _adapter(service)

    class _FakeDownloader:
        def __init__(self, _fd, _request):
            pass

        def next_chunk(self, num_retries: int = 0):
            raise HttpError(MagicMock(status=500), b"server")

    with patch("capabilities.document.drive_adapter.MediaIoBaseDownload", _FakeDownloader):
        with pytest.raises(DriveAdapterError):
            adapter.download_file("f1")


# ---------- contract ----------


def test_drive_file_dataclass_round_trip() -> None:
    f = DriveFile(
        id="f1",
        name="x.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        modified_time="2026-04-25T10:00:00Z",
    )
    assert f.id == "f1"
    assert f.size_bytes == 10
