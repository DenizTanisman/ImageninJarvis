"""Plain-data structures for the Gmail adapter."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MailSummary:
    """Lightweight Gmail message: metadata + snippet, no body."""

    id: str
    thread_id: str
    from_addr: str
    subject: str
    snippet: str
    date: str  # RFC-2822 string from the Date header
    internal_date_ms: int
