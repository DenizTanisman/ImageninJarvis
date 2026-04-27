"""Voice-friendly summarisation for capability results.

Step 6.1: when a request comes from the voice surface, dumping a JSON
``MailSummary`` to the TTS engine produces nonsense. This module reads
the structured ``Result.data`` and ``ui_type`` and returns a short Turkish
sentence the synthesiser can speak naturally.

The transformation is deterministic — no LLM round-trip — because:
- voice already pays a TTS cost; another network hop hurts UX,
- the structures we summarise are small and well-known, and
- the chat surface still gets the full data, so power users can read
  the long form there.

If a ui_type isn't recognised the formatter falls back to ``data`` if it's
a string, and to a generic "İşlem tamamlandı" otherwise.
"""
from __future__ import annotations

from typing import Any

CATEGORY_LABEL: dict[str, str] = {
    "important": "önemli",
    "dm": "kişisel",
    "promo": "promosyon",
    "other": "diğer",
}

LANG_LABEL: dict[str, str] = {
    "tr": "Türkçe",
    "en": "İngilizce",
    "de": "Almanca",
    "fr": "Fransızca",
    "es": "İspanyolca",
    "ru": "Rusça",
    "ar": "Arapça",
    "auto": "otomatik",
}


def format_for_voice(ui_type: str | None, data: Any) -> str:
    if ui_type == "MailCard":
        return _format_mail(data)
    if ui_type == "TranslationCard":
        return _format_translation(data)
    if ui_type == "EventList":
        return _format_event_list(data)
    if ui_type == "CalendarEvent":
        return _format_calendar_event(data)
    if ui_type == "DocumentAnswer":
        return _format_document_answer(data)
    if isinstance(data, str):
        return data
    return "İşlem tamamlandı."


def _format_mail(data: Any) -> str:
    if not isinstance(data, dict):
        return "Mail özeti hazır."
    categories = data.get("categories") or {}
    counts = {key: len(categories.get(key, []) or []) for key in CATEGORY_LABEL}
    total = data.get("total")
    if isinstance(total, int) and total == 0:
        return "Bu aralıkta mailin yok."
    parts = [
        f"{counts[key]} {CATEGORY_LABEL[key]}"
        for key in ("important", "dm", "promo", "other")
        if counts[key] > 0
    ]
    if not parts:
        return "Bu aralıkta mailin yok."
    summary = ", ".join(parts) + " mail var."
    needs_reply = data.get("needs_reply_count")
    if isinstance(needs_reply, int) and needs_reply > 0:
        summary += f" {needs_reply} tanesi yanıt bekliyor — okumamı ister misin?"
    return summary


def _format_translation(data: Any) -> str:
    if not isinstance(data, dict):
        return "Çeviri hazır."
    target = data.get("target_lang")
    text = data.get("translated_text") or ""
    label = LANG_LABEL.get(str(target).lower(), str(target).upper() if target else "")
    if label:
        return f"{label}: {text}"
    return text or "Çeviri hazır."


def _format_event_list(data: Any) -> str:
    if not isinstance(data, dict):
        return "Etkinlik listesi hazır."
    events = data.get("events") or []
    if not isinstance(events, list) or not events:
        return "Önümüzdeki günlerde etkinlik yok."
    count = len(events)
    if count == 1:
        only = events[0]
        return f"Bir etkinlik var: {_short_event(only)}."
    head = events[0]
    return (
        f"{count} etkinlik var. İlki {_short_event(head)}. "
        "Hepsini ister misin?"
    )


def _format_calendar_event(data: Any) -> str:
    if not isinstance(data, dict):
        return "Etkinlik kaydedildi."
    return f"Tamam, '{data.get('summary', 'etkinlik')}' kaydedildi."


def _format_document_answer(data: Any) -> str:
    if not isinstance(data, dict):
        return "Belge cevabı hazır."
    answer = data.get("answer")
    if isinstance(answer, str) and answer.strip():
        return answer.strip()
    return "Belgeden bir cevap çıkmadı."


def _short_event(event: Any) -> str:
    if not isinstance(event, dict):
        return "etkinlik"
    summary = event.get("summary") or "etkinlik"
    start = event.get("start") or ""
    if isinstance(start, str) and len(start) >= 16:
        # 2026-04-28T14:00:00+03:00 → "28 Nisan saat 14:00"
        date_part = start[:10]
        time_part = start[11:16]
        return f"{summary}, {_human_date(date_part)} saat {time_part}"
    return f"{summary}"


_TR_MONTHS = (
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
)


def _human_date(date_part: str) -> str:
    """``2026-04-28`` → ``28 Nisan``. Falls back to the raw string on
    malformed input."""
    try:
        year, month, day = date_part.split("-")
        idx = int(month) - 1
        if not 0 <= idx < 12:
            return date_part
        return f"{int(day)} {_TR_MONTHS[idx]}"
    except (ValueError, IndexError):
        return date_part
