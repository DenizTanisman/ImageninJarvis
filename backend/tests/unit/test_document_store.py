import pytest

from services.document_store import DocumentMeta, DocumentStore, DocumentStoreError


def _meta(doc_id: str = "abc") -> DocumentMeta:
    return DocumentMeta(
        doc_id=doc_id,
        original_name="x.pdf",
        mime_type="application/pdf",
        page_count=3,
        size_bytes=10,
        file_path=f"/tmp/jarvis_sandbox/{doc_id}/x.pdf",
    )


def test_register_and_get_round_trip() -> None:
    store = DocumentStore()
    store.register(_meta("a"))
    out = store.get("a")
    assert out.doc_id == "a"
    assert out.page_count == 3
    assert out.chunks == ()


def test_get_unknown_raises_document_store_error() -> None:
    store = DocumentStore()
    with pytest.raises(DocumentStoreError):
        store.get("missing")


def test_has_returns_membership() -> None:
    store = DocumentStore()
    store.register(_meta("a"))
    assert store.has("a")
    assert not store.has("b")


def test_forget_removes_entry_and_is_idempotent() -> None:
    store = DocumentStore()
    store.register(_meta("a"))
    store.forget("a")
    assert not store.has("a")
    store.forget("a")  # second call must not raise


def test_attach_chunks_replaces_chunks_only() -> None:
    store = DocumentStore()
    store.register(_meta("a"))
    store.attach_chunks("a", ("chunk-1", "chunk-2"))
    out = store.get("a")
    assert out.chunks == ("chunk-1", "chunk-2")
    assert out.page_count == 3  # other fields untouched


def test_attach_chunks_unknown_raises() -> None:
    store = DocumentStore()
    with pytest.raises(DocumentStoreError):
        store.attach_chunks("missing", ("x",))


def test_register_overwrites_same_id() -> None:
    store = DocumentStore()
    store.register(_meta("a"))
    new = DocumentMeta(
        doc_id="a",
        original_name="y.txt",
        mime_type="text/plain",
        page_count=1,
        size_bytes=5,
        file_path="/tmp/jarvis_sandbox/a/y.txt",
    )
    store.register(new)
    assert store.get("a").original_name == "y.txt"
