import base64
from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from capabilities.gmail.adapter import GmailAdapter, GmailAdapterError


def _adapter_with_send(send_response: dict | None = None) -> tuple[GmailAdapter, MagicMock]:
    service = MagicMock()
    if send_response is not None:
        service.users.return_value.messages.return_value.send.return_value.execute.return_value = (
            send_response
        )
    adapter = GmailAdapter(credentials=MagicMock(), service=service)
    return adapter, service


def test_send_reply_builds_and_calls_users_messages_send() -> None:
    adapter, service = _adapter_with_send({"id": "sent-1", "threadId": "t1"})
    payload = adapter.send_reply(
        to="alice@example.com",
        subject="Toplantı",
        body="Merhaba, evet uygundur.",
        thread_id="t1",
        in_reply_to_message_id="<orig@mail>",
    )
    assert payload == {"id": "sent-1", "threadId": "t1"}

    send_call = service.users.return_value.messages.return_value.send
    args, kwargs = send_call.call_args
    assert kwargs["userId"] == "me"
    body = kwargs["body"]
    assert body["threadId"] == "t1"

    # decode the base64url payload and verify headers (Subject may be
    # RFC-2047 quoted-printable encoded for non-ASCII chars).
    raw_decoded = base64.urlsafe_b64decode(body["raw"]).decode("utf-8", errors="replace")
    assert "To: alice@example.com" in raw_decoded
    assert raw_decoded.count("Subject: Re:") == 1
    assert "In-Reply-To: <orig@mail>" in raw_decoded
    assert "Merhaba, evet uygundur." in raw_decoded


def test_send_reply_does_not_double_prefix_re() -> None:
    adapter, service = _adapter_with_send({"id": "sent"})
    adapter.send_reply(
        to="b@x.com",
        subject="Re: zaten cevap",
        body="ok",
        thread_id="t",
    )
    body = service.users.return_value.messages.return_value.send.call_args.kwargs["body"]
    raw = base64.urlsafe_b64decode(body["raw"]).decode("utf-8")
    assert raw.lower().count("subject: re:") == 1


def test_send_reply_rejects_empty_body_or_recipient() -> None:
    adapter, _ = _adapter_with_send({"id": "x"})
    with pytest.raises(GmailAdapterError):
        adapter.send_reply(to="", subject="s", body="b", thread_id="t")
    with pytest.raises(GmailAdapterError):
        adapter.send_reply(to="a@b", subject="s", body="   ", thread_id="t")


def test_send_reply_wraps_http_error() -> None:
    service = MagicMock()
    service.users.return_value.messages.return_value.send.return_value.execute.side_effect = (
        HttpError(MagicMock(status=403), b"forbidden")
    )
    adapter = GmailAdapter(credentials=MagicMock(), service=service)
    with pytest.raises(GmailAdapterError):
        adapter.send_reply(to="a@b.com", subject="s", body="b", thread_id="t")


def test_get_full_message_returns_payload() -> None:
    service = MagicMock()
    service.users.return_value.messages.return_value.get.return_value.execute.return_value = {
        "id": "m1",
        "snippet": "snippet",
        "payload": {"mimeType": "text/plain", "body": {"data": "aGVsbG8="}},
    }
    adapter = GmailAdapter(credentials=MagicMock(), service=service)
    payload = adapter.get_full_message("m1")
    assert payload["id"] == "m1"
    service.users.return_value.messages.return_value.get.assert_called_with(
        userId="me", id="m1", format="full"
    )


def test_get_full_message_wraps_http_error() -> None:
    service = MagicMock()
    service.users.return_value.messages.return_value.get.return_value.execute.side_effect = (
        HttpError(MagicMock(status=500), b"server")
    )
    adapter = GmailAdapter(credentials=MagicMock(), service=service)
    with pytest.raises(GmailAdapterError):
        adapter.get_full_message("m1")
