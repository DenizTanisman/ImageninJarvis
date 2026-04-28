from core.voice_formatter import format_for_voice

# ---------- mail ----------


def test_mail_summarises_counts_and_reply_prompt() -> None:
    data = {
        "categories": {
            "important": [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}],
            "dm": [{"id": "5"}, {"id": "6"}],
            "promo": [{"id": "7"}] * 9,
            "other": [],
        },
        "needs_reply_count": 3,
        "total": 15,
    }
    summary = format_for_voice("MailCard", data)
    assert "4 önemli" in summary
    assert "2 kişisel" in summary
    assert "9 promosyon" in summary
    assert "3 tanesi yanıt bekliyor" in summary


def test_mail_handles_zero_total() -> None:
    data = {
        "categories": {"important": [], "dm": [], "promo": [], "other": []},
        "needs_reply_count": 0,
        "total": 0,
    }
    assert "yok" in format_for_voice("MailCard", data).lower()


def test_mail_skips_empty_categories_in_listing() -> None:
    data = {
        "categories": {
            "important": [{"id": "1"}],
            "dm": [],
            "promo": [],
            "other": [],
        },
        "needs_reply_count": 0,
        "total": 1,
    }
    summary = format_for_voice("MailCard", data)
    assert "1 önemli" in summary
    assert "0 kişisel" not in summary


# ---------- translation ----------


def test_translation_prefixes_target_language() -> None:
    data = {
        "source_text": "merhaba",
        "translated_text": "Hello",
        "source_lang": "tr",
        "target_lang": "en",
    }
    out = format_for_voice("TranslationCard", data)
    assert out.startswith("İngilizce:")
    assert "Hello" in out


def test_translation_unknown_lang_uses_uppercase_code() -> None:
    data = {
        "translated_text": "ok",
        "source_lang": "auto",
        "target_lang": "ja",
    }
    out = format_for_voice("TranslationCard", data)
    assert "JA" in out


# ---------- event list / calendar event ----------


def test_event_list_reads_first_event_when_multiple() -> None:
    data = {
        "events": [
            {
                "id": "e1",
                "summary": "Sunum",
                "start": "2026-04-28T14:00:00+03:00",
                "end": "2026-04-28T15:00:00+03:00",
            },
            {
                "id": "e2",
                "summary": "Sync",
                "start": "2026-04-29T10:00:00+03:00",
                "end": "2026-04-29T10:30:00+03:00",
            },
        ],
        "days": 7,
    }
    out = format_for_voice("EventList", data)
    assert "2 etkinlik var" in out
    assert "Sunum" in out
    assert "28 Nisan" in out
    assert "saat 14:00" in out


def test_event_list_handles_single_event() -> None:
    data = {
        "events": [
            {
                "id": "e1",
                "summary": "Sunum",
                "start": "2026-04-28T14:00:00+03:00",
                "end": "2026-04-28T15:00:00+03:00",
            }
        ],
        "days": 7,
    }
    out = format_for_voice("EventList", data)
    assert "Bir etkinlik var" in out


def test_event_list_empty_returns_friendly_message() -> None:
    data = {"events": [], "days": 7}
    out = format_for_voice("EventList", data)
    assert "etkinlik yok" in out


def test_calendar_event_create_confirmation() -> None:
    data = {
        "id": "e1",
        "summary": "Q2 review",
        "start": "2026-04-28T14:00:00+03:00",
        "end": "2026-04-28T15:00:00+03:00",
    }
    out = format_for_voice("CalendarEvent", data)
    assert "Q2 review" in out
    assert "kaydedildi" in out


# ---------- document ----------


def test_document_answer_passes_through() -> None:
    data = {"answer": "Belgede üç ana başlık var.", "doc_id": "x"}
    assert format_for_voice("DocumentAnswer", data) == "Belgede üç ana başlık var."


def test_document_answer_empty_returns_fallback() -> None:
    out = format_for_voice("DocumentAnswer", {"answer": "  "})
    assert "cevap çıkmadı" in out.lower()


# ---------- fallbacks ----------


def test_string_data_passes_through_for_text_ui_type() -> None:
    assert format_for_voice("text", "Selam dünya.") == "Selam dünya."


def test_unknown_ui_type_with_string_data_passes_through() -> None:
    assert format_for_voice("Mystery", "ok") == "ok"


def test_unknown_ui_type_with_dict_data_returns_generic_message() -> None:
    assert format_for_voice("Mystery", {"x": 1}) == "İşlem tamamlandı."


def test_none_data_with_unknown_ui_type_returns_generic_message() -> None:
    assert format_for_voice(None, None) == "İşlem tamamlandı."
