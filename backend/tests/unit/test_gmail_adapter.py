from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from capabilities.gmail.adapter import GmailAdapter, GmailAdapterError
from capabilities.gmail.models import MailSummary


def _make_message_payload(
    *,
    msg_id: str,
    thread_id: str = "thr",
    from_addr: str = "test@example.com",
    subject: str = "Hello",
    snippet: str = "Hi there",
    date: str = "Tue, 28 Apr 2026 10:00:00 +0300",
    internal_ms: int = 1745835600000,
) -> dict:
    return {
        "id": msg_id,
        "threadId": thread_id,
        "snippet": snippet,
        "internalDate": str(internal_ms),
        "payload": {
            "headers": [
                {"name": "From", "value": from_addr},
                {"name": "Subject", "value": subject},
                {"name": "Date", "value": date},
            ]
        },
    }


def _service_with_messages(payloads: list[dict]) -> MagicMock:
    """Build a MagicMock that mirrors the Gmail service.users().messages() chain."""
    service = MagicMock()
    list_response = {
        "messages": [{"id": p["id"], "threadId": p.get("threadId", "")} for p in payloads]
    }
    service.users.return_value.messages.return_value.list.return_value.execute.return_value = (
        list_response
    )
    get_executes = [MagicMock(execute=MagicMock(return_value=p)) for p in payloads]
    get_call = MagicMock(side_effect=get_executes)
    service.users.return_value.messages.return_value.get = get_call
    return service


def _adapter(service: MagicMock) -> GmailAdapter:
    return GmailAdapter(credentials=MagicMock(), service=service)


def test_list_messages_builds_search_query() -> None:
    service = _service_with_messages([])
    adapter = _adapter(service)
    adapter.list_messages(after="2026-04-20", before="2026-04-25", max_results=10)
    list_call = service.users.return_value.messages.return_value.list
    list_call.assert_called_once_with(
        userId="me", q="after:2026-04-20 before:2026-04-25", maxResults=10
    )


def test_list_messages_returns_summaries_with_parsed_headers() -> None:
    payloads = [
        _make_message_payload(msg_id="m1", from_addr="alice@example.com", subject="Hi"),
        _make_message_payload(msg_id="m2", from_addr="bob@example.com", subject="Hey"),
    ]
    adapter = _adapter(_service_with_messages(payloads))
    summaries = adapter.list_messages(after="2026-04-20", before="2026-04-25")
    assert len(summaries) == 2
    assert all(isinstance(s, MailSummary) for s in summaries)
    assert summaries[0].from_addr == "alice@example.com"
    assert summaries[0].subject == "Hi"
    assert summaries[1].id == "m2"


def test_list_messages_only_fetches_metadata_format() -> None:
    payloads = [_make_message_payload(msg_id="m1")]
    adapter = _adapter(_service_with_messages(payloads))
    adapter.list_messages(after="2026-04-20", before="2026-04-25")
    get_call = adapter._service.users.return_value.messages.return_value.get
    get_call.assert_called_once_with(
        userId="me",
        id="m1",
        format="metadata",
        metadataHeaders=["From", "Subject", "Date"],
    )


def test_list_messages_returns_empty_for_zero_max() -> None:
    adapter = _adapter(_service_with_messages([_make_message_payload(msg_id="m1")]))
    assert adapter.list_messages(after="x", before="y", max_results=0) == []


def test_list_messages_skips_individual_get_failures() -> None:
    payloads = [_make_message_payload(msg_id="m1"), _make_message_payload(msg_id="m2")]
    service = _service_with_messages(payloads)

    failing_get = MagicMock()
    failing_get.execute.side_effect = HttpError(MagicMock(status=500), b"boom")
    ok_get = MagicMock()
    ok_get.execute.return_value = payloads[1]
    service.users.return_value.messages.return_value.get = MagicMock(
        side_effect=[failing_get, ok_get]
    )
    adapter = _adapter(service)
    summaries = adapter.list_messages(after="x", before="y")
    assert len(summaries) == 1
    assert summaries[0].id == "m2"


def test_list_messages_raises_when_list_call_fails() -> None:
    service = MagicMock()
    failing = MagicMock()
    failing.execute.side_effect = HttpError(MagicMock(status=503), b"unavailable")
    service.users.return_value.messages.return_value.list.return_value = failing
    adapter = _adapter(service)
    with pytest.raises(GmailAdapterError):
        adapter.list_messages(after="x", before="y")


def test_parse_handles_missing_optional_fields() -> None:
    payload = {
        "id": "m1",
        "snippet": "snippet",
        "internalDate": "0",
        "payload": {"headers": []},
    }
    service = MagicMock()
    service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        "messages": [{"id": "m1"}]
    }
    service.users.return_value.messages.return_value.get.return_value.execute.return_value = (
        payload
    )
    adapter = _adapter(service)
    out = adapter.list_messages(after="x", before="y")
    assert out[0].subject == "(no subject)"
    assert out[0].from_addr == ""
    assert out[0].thread_id == ""
