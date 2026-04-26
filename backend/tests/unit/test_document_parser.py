import io

import pytest
from pypdf import PdfWriter

from capabilities.document.parser import (
    DocumentParseError,
    chunk_text,
    parse_and_chunk,
    parse_pdf,
    parse_txt,
)

# ---------- chunk_text ----------


def test_chunk_text_empty_returns_empty_tuple() -> None:
    assert chunk_text("") == ()
    assert chunk_text("   \n  ") == ()


def test_chunk_text_short_returns_single_chunk() -> None:
    out = chunk_text("hello world", chunk_chars=100, overlap_chars=10)
    assert out == ("hello world",)


def test_chunk_text_splits_with_overlap() -> None:
    text = "abcdefghij" * 5  # 50 chars
    out = chunk_text(text, chunk_chars=20, overlap_chars=5)
    # First chunk 0-20, next starts at 20-5=15
    assert out[0] == text[0:20]
    assert out[1] == text[15:35]
    assert out[2] == text[30:50]
    assert len(out) == 3
    # Each chunk overlaps the previous by 5 chars
    assert out[0][-5:] == out[1][:5]


def test_chunk_text_window_advances_even_at_end() -> None:
    text = "x" * 100
    out = chunk_text(text, chunk_chars=30, overlap_chars=10)
    assert all(len(c) <= 30 for c in out)
    assert "".join(out).count("x") >= 100  # every char covered (with overlap)


def test_chunk_text_rejects_overlap_geq_chunk() -> None:
    with pytest.raises(ValueError):
        chunk_text("hi", chunk_chars=10, overlap_chars=10)


def test_chunk_text_rejects_zero_chunk_size() -> None:
    with pytest.raises(ValueError):
        chunk_text("hi", chunk_chars=0, overlap_chars=0)


# ---------- parse_txt ----------


def test_parse_txt_utf8(tmp_path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("Merhaba — günaydın", encoding="utf-8")
    assert parse_txt(p) == "Merhaba — günaydın"


def test_parse_txt_handles_utf8_bom(tmp_path) -> None:
    p = tmp_path / "x.txt"
    p.write_bytes(b"\xef\xbb\xbfHello")
    assert parse_txt(p) == "Hello"


def test_parse_txt_falls_back_to_latin1(tmp_path) -> None:
    p = tmp_path / "x.txt"
    # 0xa9 (©) is valid latin-1 but not valid UTF-8 standalone
    p.write_bytes(b"caf\xe9")
    assert "caf" in parse_txt(p)


# ---------- parse_pdf ----------


def _blank_pdf_bytes(pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_parse_pdf_blank_pages_returns_empty_string(tmp_path) -> None:
    p = tmp_path / "x.pdf"
    p.write_bytes(_blank_pdf_bytes(pages=2))
    out = parse_pdf(p)
    assert out == ""


def test_parse_pdf_raises_on_corrupt_file(tmp_path) -> None:
    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF-1.4 not actually a pdf")
    with pytest.raises(DocumentParseError):
        parse_pdf(p)


def test_parse_pdf_raises_on_missing_file(tmp_path) -> None:
    with pytest.raises(DocumentParseError):
        parse_pdf(tmp_path / "missing.pdf")


# ---------- parse_and_chunk ----------


def test_parse_and_chunk_txt(tmp_path) -> None:
    text = "Bu bir test belgesidir.\n" * 1000  # 24000 chars
    p = tmp_path / "x.txt"
    p.write_text(text, encoding="utf-8")
    out = parse_and_chunk(file_path=p, mime_type="text/plain")
    assert len(out) >= 1
    assert all(isinstance(c, str) and c for c in out)


def test_parse_and_chunk_rejects_unknown_mime(tmp_path) -> None:
    p = tmp_path / "x.bin"
    p.write_bytes(b"hello")
    with pytest.raises(DocumentParseError):
        parse_and_chunk(file_path=p, mime_type="application/zip")
