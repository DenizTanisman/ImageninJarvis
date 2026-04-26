import ssl
from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from capabilities.calendar.adapter import (
    CalendarAdapter,
    CalendarAdapterError,
)
from capabilities.calendar.models import CalendarEvent


def _adapter(service: MagicMock | None = None) -> tuple[CalendarAdapter, MagicMock]:
    svc = service or MagicMock()
    return CalendarAdapter(credentials=MagicMock(), service=svc), svc


def _event_payload(
    *,
    event_id: str = "e1",
    summary: str = "Sunum",
    start: str = "2026-04-28T14:00:00+03:00",
    end: str = "2026-04-28T15:00:00+03:00",
    description: str = "Q2 sprint",
) -> dict:
    return {
        "id": event_id,
        "summary": summary,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
        "description": description,
        "htmlLink": "https://calendar.google.com/event?eid=x",
    }


# ---------- list ----------


def test_list_events_returns_parsed_models() -> None:
    service = MagicMock()
    service.events.return_value.list.return_value.execute.return_value = {
        "items": [_event_payload(event_id="e1"), _event_payload(event_id="e2")]
    }
    adapter, _ = _adapter(service)
    events = adapter.list_events(days=7)
    assert len(events) == 2
    assert all(isinstance(e, CalendarEvent) for e in events)
    assert events[0].id == "e1"
    assert events[0].summary == "Sunum"


def test_list_events_passes_window_and_ordering() -> None:
    service = MagicMock()
    service.events.return_value.list.return_value.execute.return_value = {"items": []}
    adapter, _ = _adapter(service)
    adapter.list_events(days=7)
    list_call = service.events.return_value.list
    kwargs = list_call.call_args.kwargs
    assert kwargs["calendarId"] == "primary"
    assert kwargs["singleEvents"] is True
    assert kwargs["orderBy"] == "startTime"
    assert "timeMin" in kwargs and "timeMax" in kwargs
    # timeMax must be after timeMin
    assert kwargs["timeMin"] < kwargs["timeMax"]


def test_list_events_returns_empty_for_zero_days() -> None:
    adapter, _ = _adapter()
    assert adapter.list_events(days=0) == []


def test_list_events_skips_payloads_missing_id() -> None:
    service = MagicMock()
    service.events.return_value.list.return_value.execute.return_value = {
        "items": [
            {"summary": "no id"},  # malformed
            _event_payload(event_id="e2"),
        ]
    }
    adapter, _ = _adapter(service)
    events = adapter.list_events()
    assert len(events) == 1
    assert events[0].id == "e2"


def test_list_events_wraps_http_error() -> None:
    service = MagicMock()
    service.events.return_value.list.return_value.execute.side_effect = HttpError(
        MagicMock(status=500), b"server"
    )
    adapter, _ = _adapter(service)
    with pytest.raises(CalendarAdapterError):
        adapter.list_events()


def test_list_events_wraps_ssl_error() -> None:
    service = MagicMock()
    service.events.return_value.list.return_value.execute.side_effect = ssl.SSLEOFError(
        "EOF"
    )
    adapter, _ = _adapter(service)
    with pytest.raises(CalendarAdapterError):
        adapter.list_events()


# ---------- create ----------


def test_create_event_posts_body_and_returns_model() -> None:
    service = MagicMock()
    service.events.return_value.insert.return_value.execute.return_value = (
        _event_payload(event_id="new-1")
    )
    adapter, _ = _adapter(service)
    out = adapter.create_event(
        summary="Sunum",
        start="2026-04-28T14:00:00+03:00",
        end="2026-04-28T15:00:00+03:00",
        description="Q2 sprint",
    )
    assert out.id == "new-1"
    insert_call = service.events.return_value.insert
    body = insert_call.call_args.kwargs["body"]
    assert body["summary"] == "Sunum"
    assert body["start"]["dateTime"] == "2026-04-28T14:00:00+03:00"
    assert body["end"]["dateTime"] == "2026-04-28T15:00:00+03:00"
    assert body["description"] == "Q2 sprint"


def test_create_event_rejects_empty_summary() -> None:
    adapter, _ = _adapter()
    with pytest.raises(CalendarAdapterError):
        adapter.create_event(summary="   ", start="a", end="b")


def test_create_event_rejects_missing_times() -> None:
    adapter, _ = _adapter()
    with pytest.raises(CalendarAdapterError):
        adapter.create_event(summary="x", start="", end="b")


def test_create_event_wraps_http_error() -> None:
    service = MagicMock()
    service.events.return_value.insert.return_value.execute.side_effect = HttpError(
        MagicMock(status=403), b"forbidden"
    )
    adapter, _ = _adapter(service)
    with pytest.raises(CalendarAdapterError):
        adapter.create_event(
            summary="x",
            start="2026-04-28T14:00:00+03:00",
            end="2026-04-28T15:00:00+03:00",
        )


# ---------- update ----------


def test_update_event_patches_only_set_fields() -> None:
    service = MagicMock()
    service.events.return_value.patch.return_value.execute.return_value = (
        _event_payload(event_id="e1", summary="Yeni başlık")
    )
    adapter, _ = _adapter(service)
    out = adapter.update_event("e1", summary="Yeni başlık")
    assert out.summary == "Yeni başlık"
    body = service.events.return_value.patch.call_args.kwargs["body"]
    assert body == {"summary": "Yeni başlık"}


def test_update_event_includes_start_end_when_provided() -> None:
    service = MagicMock()
    service.events.return_value.patch.return_value.execute.return_value = (
        _event_payload(event_id="e1")
    )
    adapter, _ = _adapter(service)
    adapter.update_event(
        "e1",
        start="2026-04-29T10:00:00+03:00",
        end="2026-04-29T11:00:00+03:00",
    )
    body = service.events.return_value.patch.call_args.kwargs["body"]
    assert body == {
        "start": {"dateTime": "2026-04-29T10:00:00+03:00"},
        "end": {"dateTime": "2026-04-29T11:00:00+03:00"},
    }


def test_update_event_rejects_empty_id() -> None:
    adapter, _ = _adapter()
    with pytest.raises(CalendarAdapterError):
        adapter.update_event("", summary="x")


def test_update_event_rejects_no_fields_set() -> None:
    adapter, _ = _adapter()
    with pytest.raises(CalendarAdapterError):
        adapter.update_event("e1")


def test_update_event_wraps_http_error() -> None:
    service = MagicMock()
    service.events.return_value.patch.return_value.execute.side_effect = HttpError(
        MagicMock(status=404), b"not found"
    )
    adapter, _ = _adapter(service)
    with pytest.raises(CalendarAdapterError):
        adapter.update_event("e1", summary="x")


# ---------- delete ----------


def test_delete_event_calls_delete_with_event_id() -> None:
    service = MagicMock()
    service.events.return_value.delete.return_value.execute.return_value = ""
    adapter, _ = _adapter(service)
    adapter.delete_event("e1")
    delete_call = service.events.return_value.delete
    delete_call.assert_called_with(calendarId="primary", eventId="e1")


def test_delete_event_rejects_empty_id() -> None:
    adapter, _ = _adapter()
    with pytest.raises(CalendarAdapterError):
        adapter.delete_event("")


def test_delete_event_wraps_http_error() -> None:
    service = MagicMock()
    service.events.return_value.delete.return_value.execute.side_effect = HttpError(
        MagicMock(status=410), b"gone"
    )
    adapter, _ = _adapter(service)
    with pytest.raises(CalendarAdapterError):
        adapter.delete_event("e1")
