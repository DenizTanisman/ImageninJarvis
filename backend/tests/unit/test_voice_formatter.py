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
    assert "4 important" in summary
    assert "2 personal" in summary
    assert "9 promotional" in summary
    assert "3 of them need a reply" in summary


def test_mail_handles_zero_total() -> None:
    data = {
        "categories": {"important": [], "dm": [], "promo": [], "other": []},
        "needs_reply_count": 0,
        "total": 0,
    }
    assert "no mail" in format_for_voice("MailCard", data).lower()


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
    assert "1 important" in summary
    assert "0 personal" not in summary


# ---------- translation ----------


def test_translation_prefixes_target_language() -> None:
    data = {
        "source_text": "merhaba",
        "translated_text": "Hello",
        "source_lang": "tr",
        "target_lang": "en",
    }
    out = format_for_voice("TranslationCard", data)
    assert out.startswith("English:")
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
    assert "2 events" in out
    assert "Sunum" in out
    assert "April 28" in out
    assert "at 14:00" in out


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
    assert "one event" in out


def test_event_list_empty_returns_friendly_message() -> None:
    data = {"events": [], "days": 7}
    out = format_for_voice("EventList", data)
    assert "No events" in out


def test_calendar_event_create_confirmation() -> None:
    data = {
        "id": "e1",
        "summary": "Q2 review",
        "start": "2026-04-28T14:00:00+03:00",
        "end": "2026-04-28T15:00:00+03:00",
    }
    out = format_for_voice("CalendarEvent", data)
    assert "Q2 review" in out
    assert "saved" in out.lower()


# ---------- document ----------


def test_document_answer_passes_through() -> None:
    data = {"answer": "The document has three main headings.", "doc_id": "x"}
    assert format_for_voice("DocumentAnswer", data) == "The document has three main headings."


def test_document_answer_empty_returns_fallback() -> None:
    out = format_for_voice("DocumentAnswer", {"answer": "  "})
    assert "no answer" in out.lower()


# ---------- fallbacks ----------


def test_string_data_passes_through_for_text_ui_type() -> None:
    assert format_for_voice("text", "Hello world.") == "Hello world."


def test_unknown_ui_type_with_string_data_passes_through() -> None:
    assert format_for_voice("Mystery", "ok") == "ok"


def test_unknown_ui_type_with_dict_data_returns_generic_message() -> None:
    assert format_for_voice("Mystery", {"x": 1}) == "Done."


def test_none_data_with_unknown_ui_type_returns_generic_message() -> None:
    assert format_for_voice(None, None) == "Done."


def test_journal_report_with_count() -> None:
    out = format_for_voice(
        "JournalReportCard",
        {"tag": "/detail", "entry_count": 6, "markdown": "# Report\n..."},
    )
    assert "/detail" in out
    assert "6" in out


def test_journal_report_without_count_falls_back() -> None:
    assert format_for_voice("JournalReportCard", {"tag": "/todo"}) == "/todo report ready."


def test_journal_report_with_non_dict_data_safe_default() -> None:
    assert format_for_voice("JournalReportCard", None) == "Journal report ready."
