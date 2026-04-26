"""Document parser + chunker.

Step 5.4: extract plain text from a PDF / TXT and split it into
overlapping windows so the QA strategy can fit the most relevant slices
into the LLM prompt without exceeding the context budget.

The chunk window is character-based as a pragmatic stand-in for the
"8000 tokens" target in CLAUDE.md — characters are deterministic and
mock-friendly, while tokens depend on the model's tokenizer. Numbers
chosen so 3 chunks (the MVP RAG ceiling) fit comfortably in Gemini 2.5
Flash's context with room left for the question + answer.
"""
from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

DEFAULT_CHUNK_CHARS = 8000
DEFAULT_OVERLAP_CHARS = 200


class DocumentParseError(RuntimeError):
    pass


def parse_pdf(path: str | Path) -> str:
    try:
        reader = PdfReader(str(path))
    except (PdfReadError, OSError) as exc:
        raise DocumentParseError(f"PDF açılamadı: {exc}") from exc
    pages: list[str] = []
    for page in reader.pages:
        try:
            extracted = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001 — pypdf raises a wide range
            raise DocumentParseError(f"PDF parse hatası: {exc}") from exc
        if extracted:
            pages.append(extracted)
    return "\n\n".join(pages)


def parse_txt(path: str | Path) -> str:
    raw = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise DocumentParseError("Metin dosyası UTF-8 / Latin-1 olarak çözülemedi")


def chunk_text(
    text: str,
    *,
    chunk_chars: int = DEFAULT_CHUNK_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> tuple[str, ...]:
    """Split ``text`` into overlapping windows.

    Empty / whitespace-only input returns an empty tuple so callers don't
    end up with a single useless chunk. ``overlap_chars`` must be smaller
    than ``chunk_chars`` (otherwise the window never advances)."""
    if chunk_chars <= 0:
        raise ValueError("chunk_chars must be positive")
    if overlap_chars < 0 or overlap_chars >= chunk_chars:
        raise ValueError("overlap_chars must be in [0, chunk_chars)")
    cleaned = text.strip()
    if not cleaned:
        return ()
    if len(cleaned) <= chunk_chars:
        return (cleaned,)

    chunks: list[str] = []
    step = chunk_chars - overlap_chars
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_chars, len(cleaned))
        chunks.append(cleaned[start:end])
        if end >= len(cleaned):
            break
        start += step
    return tuple(chunks)


def parse_and_chunk(
    *,
    file_path: str | Path,
    mime_type: str,
) -> tuple[str, ...]:
    if mime_type == "application/pdf":
        text = parse_pdf(file_path)
    elif mime_type == "text/plain":
        text = parse_txt(file_path)
    else:
        raise DocumentParseError(f"Desteklenmeyen mime type: {mime_type}")
    return chunk_text(text)
