"""Voice-friendly summarisation for capability results.

Step 6.1: when a request comes from the voice surface, dumping a JSON
``MailSummary`` to the TTS engine produces nonsense. This module reads
the structured ``Result.data`` and ``ui_type`` and returns a short English
sentence the synthesiser can speak naturally.

The transformation is deterministic — no LLM round-trip — because:
- voice already pays a TTS cost; another network hop hurts UX,
- the structures we summarise are small and well-known, and
- the chat surface still gets the full data, so power users can read
  the long form there.

If a ui_type isn't recognised the formatter falls back to ``data`` if it's
a string, and to a generic "Done." otherwise.
"""
from __future__ import annotations

from typing import Any

CATEGORY_LABEL: dict[str, str] = {
    "important": "important",
    "dm": "personal",
    "promo": "promotional",
    "other": "other",
}

LANG_LABEL: dict[str, str] = {
    "tr": "Turkish",
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "ru": "Russian",
    "ar": "Arabic",
    "auto": "auto",
}


def format_for_voice(
    ui_type: str | None,
    data: Any,
    meta: dict[str, Any] | None = None,
) -> str:
    if ui_type == "MailCard":
        return _format_mail(data)
    if ui_type == "MailDraftCard":
        return _format_mail_draft(data)
    if ui_type == "TranslationCard":
        return _format_translation(data)
    if ui_type == "EventList":
        return _format_event_list(data)
    if ui_type == "CalendarEvent":
        return _format_calendar_event(data, meta)
    if ui_type == "DocumentAnswer":
        return _format_document_answer(data)
    if ui_type == "JournalReportCard":
        return _format_journal_report(data)
    if isinstance(data, str):
        return data
    return "Done."


def _format_mail(data: Any) -> str:
    if not isinstance(data, dict):
        return "Mail summary ready."
    categories = data.get("categories") or {}
    counts = {key: len(categories.get(key, []) or []) for key in CATEGORY_LABEL}
    total = data.get("total")
    if isinstance(total, int) and total == 0:
        return "You have no mail in this range."
    parts = [
        f"{counts[key]} {CATEGORY_LABEL[key]}"
        for key in ("important", "dm", "promo", "other")
        if counts[key] > 0
    ]
    if not parts:
        return "You have no mail in this range."
    summary = "You have " + ", ".join(parts) + " mail."
    needs_reply = data.get("needs_reply_count")
    if isinstance(needs_reply, int) and needs_reply > 0:
        summary += f" {needs_reply} of them need a reply — want me to read them?"
    return summary


def _format_mail_draft(data: Any) -> str:
    if not isinstance(data, dict):
        return "Mail draft ready."
    to = data.get("to") or ""
    subject = data.get("subject") or ""
    if to and subject:
        return (
            f"I drafted a mail to {to} with subject '{subject}'. "
            "You can edit and confirm it on the card in chat."
        )
    if to:
        return (
            f"I drafted a mail to {to}. You can confirm it on the "
            "card in chat."
        )
    return "Mail draft ready — you can confirm it on the card in chat."


def _format_translation(data: Any) -> str:
    if not isinstance(data, dict):
        return "Translation ready."
    target = data.get("target_lang")
    text = data.get("translated_text") or ""
    label = LANG_LABEL.get(str(target).lower(), str(target).upper() if target else "")
    if label:
        return f"{label}: {text}"
    return text or "Translation ready."


def _format_event_list(data: Any) -> str:
    if not isinstance(data, dict):
        return "Event list ready."
    events = data.get("events") or []
    if not isinstance(events, list) or not events:
        return "No events on the calendar in the days ahead."
    count = len(events)
    if count == 1:
        only = events[0]
        return f"You have one event: {_short_event(only)}."
    head = events[0]
    return (
        f"You have {count} events. The first is {_short_event(head)}. "
        "Want me to read all of them?"
    )


def _format_calendar_event(data: Any, meta: dict[str, Any] | None = None) -> str:
    if not isinstance(data, dict):
        return "Event saved."
    summary = data.get("summary", "event")
    action = (meta or {}).get("action")
    if action == "delete_proposal":
        # Chat surface shows a card with a Delete button; voice surface
        # asks the user to confirm there since multi-turn voice delete
        # confirmation is deferred to v2.
        return (
            f"You're about to delete the event '{summary}'. Please "
            "confirm on the card in chat."
        )
    if action == "update":
        return f"'{summary}' updated."
    return f"Done — '{summary}' saved."


def _format_journal_report(data: Any) -> str:
    """One-sentence headline; chat surface still shows the full markdown."""
    if not isinstance(data, dict):
        return "Journal report ready."
    tag = data.get("tag") or "/detail"
    count = data.get("entry_count")
    if isinstance(count, int) and count > 0:
        return f"{tag} report ready — based on {count} journal entries."
    return f"{tag} report ready."


def _format_document_answer(data: Any) -> str:
    if not isinstance(data, dict):
        return "Document answer ready."
    answer = data.get("answer")
    if isinstance(answer, str) and answer.strip():
        return answer.strip()
    return "No answer could be derived from the document."


def _short_event(event: Any) -> str:
    if not isinstance(event, dict):
        return "event"
    summary = event.get("summary") or "event"
    start = event.get("start") or ""
    if isinstance(start, str) and len(start) >= 16:
        # 2026-04-28T14:00:00+03:00 → "April 28 at 14:00"
        date_part = start[:10]
        time_part = start[11:16]
        return f"{summary}, {_human_date(date_part)} at {time_part}"
    return f"{summary}"


_EN_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def _human_date(date_part: str) -> str:
    """``2026-04-28`` → ``April 28``. Falls back to the raw string on
    malformed input."""
    try:
        year, month, day = date_part.split("-")
        idx = int(month) - 1
        if not 0 <= idx < 12:
            return date_part
        return f"{_EN_MONTHS[idx]} {int(day)}"
    except (ValueError, IndexError):
        return date_part
