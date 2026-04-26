import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.dependencies import get_document_store, get_sandbox_root
from app.main import app
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


def _pdf_bytes(pages: int = 2) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_upload_pdf_registers_doc_and_writes_to_sandbox(
    client: TestClient, tmp_path: Path, store: DocumentStore
) -> None:
    pdf = _pdf_bytes(pages=3)
    response = client.post(
        "/upload",
        files={"file": ("plan.pdf", pdf, "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mime_type"] == "application/pdf"
    assert body["page_count"] == 3
    assert body["original_name"] == "plan.pdf"
    assert body["size_bytes"] == len(pdf)

    doc_id = body["doc_id"]
    assert store.has(doc_id)
    meta = store.get(doc_id)
    # Step 5.7: sandbox cleanup runs in the ingest finally block, so the
    # file should NOT be on disk anymore even though metadata + chunks
    # are still queryable via the store.
    assert not Path(meta.file_path).exists()
    assert not (tmp_path / doc_id).exists()
    assert len(meta.chunks) == 0  # blank pages produce no extractable text


def test_upload_txt_returns_page_count_one(
    client: TestClient, store: DocumentStore
) -> None:
    txt = b"Merhaba, bu bir test belgesi.\n" * 50
    response = client.post(
        "/upload",
        files={"file": ("notes.txt", txt, "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mime_type"] == "text/plain"
    assert body["page_count"] == 1


def test_upload_attaches_chunks_to_doc_store(
    client: TestClient, store: DocumentStore
) -> None:
    """5.4: upload calls parser → attach_chunks; QA strategy will read
    these later without re-parsing."""
    txt = ("Bu bir paragraf.\n" * 600).encode("utf-8")
    response = client.post(
        "/upload",
        files={"file": ("doc.txt", txt, "text/plain")},
    )
    assert response.status_code == 200
    meta = store.get(response.json()["doc_id"])
    assert len(meta.chunks) >= 1
    # Combined chunk content covers the whole document.
    assert "Bu bir paragraf." in meta.chunks[0]


def test_upload_rejects_unsupported_mime_via_content_sniffing(
    client: TestClient,
) -> None:
    """Even when the client lies about content-type, the body sniff
    catches it (PNG header here)."""
    png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    response = client.post(
        "/upload",
        files={"file": ("logo.pdf", png_header, "application/pdf")},
    )
    assert response.status_code == 415


def test_upload_rejects_oversize(client: TestClient) -> None:
    big = b"x" * (10 * 1024 * 1024 + 1)
    response = client.post(
        "/upload",
        files={"file": ("huge.txt", big, "text/plain")},
    )
    assert response.status_code == 413


def test_upload_rejects_empty_file(client: TestClient) -> None:
    response = client.post(
        "/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 400


def test_upload_rejects_corrupt_pdf(client: TestClient) -> None:
    """Body starts with %PDF- so the sniffer accepts it as PDF, but pypdf
    can't parse the header → 422 instead of crashing the route."""
    bad = b"%PDF-1.4\nthis is not actually a pdf"
    response = client.post(
        "/upload",
        files={"file": ("bad.pdf", bad, "application/pdf")},
    )
    assert response.status_code == 422


def test_upload_sanitizes_filename_against_traversal(
    client: TestClient, tmp_path: Path, store: DocumentStore
) -> None:
    txt = b"hello"
    response = client.post(
        "/upload",
        files={"file": ("../../etc/passwd", txt, "text/plain")},
    )
    assert response.status_code == 200
    meta = store.get(response.json()["doc_id"])
    assert ".." not in meta.original_name
    assert "/" not in meta.original_name
    # File lives inside the sandbox, not at /etc.
    assert str(tmp_path) in meta.file_path
