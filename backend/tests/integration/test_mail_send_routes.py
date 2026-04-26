import base64
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import (
    get_draft_generator,
    get_gmail_adapter_factory,
    get_oauth_service,
)
from app.main import app
from capabilities.gmail.adapter import GmailAdapterError
from capabilities.gmail.draft import DraftGenerator, DraftGeneratorError, ReplyDraft


@pytest.fixture()
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def _override_oauth(can_send: bool) -> MagicMock:
    fake = MagicMock()
    if can_send:
        scopes = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
        ]
        fake.credentials_for.return_value = MagicMock(scopes=scopes)
    else:
        fake.credentials_for.return_value = MagicMock(
            scopes=["https://www.googleapis.com/auth/gmail.readonly"]
        )
    app.dependency_overrides[get_oauth_service] = lambda: fake
    return fake


def _override_oauth_disconnected() -> None:
    fake = MagicMock()
    fake.credentials_for.return_value = None
    app.dependency_overrides[get_oauth_service] = lambda: fake


def _override_drafts(returning: ReplyDraft | Exception):
    fake = MagicMock(spec=DraftGenerator)
    if isinstance(returning, Exception):
        fake.generate = AsyncMock(side_effect=returning)
    else:
        fake.generate = AsyncMock(return_value=returning)
    app.dependency_overrides[get_draft_generator] = lambda: fake
    return fake


def _override_adapter(adapter: MagicMock) -> None:
    app.dependency_overrides[get_gmail_adapter_factory] = lambda: (lambda creds: adapter)


def _full_message_payload(*, msg_id: str = "m1") -> dict:
    return {
        "id": msg_id,
        "threadId": "t1",
        "snippet": "snippet",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "Test User <test@example.com>"},
                {"name": "Subject", "value": "Toplantı"},
                {"name": "Date", "value": "Tue, 28 Apr 2026 10:00:00 +0300"},
            ],
            "body": {
                "data": base64.urlsafe_b64encode(b"Yarin uygun mu?").decode("ascii")
            },
        },
    }


def test_drafts_returns_drafts_for_each_message(client: TestClient) -> None:
    _override_oauth(can_send=True)
    adapter = MagicMock()
    adapter.get_full_message.side_effect = [
        _full_message_payload(msg_id="m1"),
        _full_message_payload(msg_id="m2"),
    ]
    _override_adapter(adapter)
    fake_drafts = _override_drafts(
        ReplyDraft(
            message_id="m1",
            thread_id="t1",
            to="test@example.com",
            subject="Toplantı",
            body="Cevap",
        )
    )

    response = client.post(
        "/mail/drafts",
        json={"message_ids": ["m1", "m2"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["drafts"]) == 2
    assert body["failures"] == []
    assert fake_drafts.generate.await_count == 2


def test_drafts_collects_failures_individually(client: TestClient) -> None:
    _override_oauth(can_send=True)
    adapter = MagicMock()
    adapter.get_full_message.side_effect = [
        _full_message_payload(msg_id="m1"),
        GmailAdapterError("nope"),
    ]
    _override_adapter(adapter)
    _override_drafts(
        ReplyDraft(
            message_id="m1",
            thread_id="t1",
            to="x@y.com",
            subject="s",
            body="ok",
        )
    )
    response = client.post("/mail/drafts", json={"message_ids": ["m1", "m2"]})
    assert response.status_code == 200
    body = response.json()
    assert len(body["drafts"]) == 1
    assert body["failures"] == ["m2"]


def test_drafts_returns_401_when_disconnected(client: TestClient) -> None:
    _override_oauth_disconnected()
    _override_adapter(MagicMock())
    _override_drafts(
        ReplyDraft(message_id="m", thread_id="t", to="x", subject="s", body="b")
    )
    response = client.post("/mail/drafts", json={"message_ids": ["m1"]})
    assert response.status_code == 401


def test_drafts_propagates_generator_failure_into_failures(client: TestClient) -> None:
    _override_oauth(can_send=True)
    adapter = MagicMock()
    adapter.get_full_message.return_value = _full_message_payload(msg_id="m1")
    _override_adapter(adapter)
    _override_drafts(DraftGeneratorError("offline"))
    response = client.post("/mail/drafts", json={"message_ids": ["m1"]})
    assert response.status_code == 200
    body = response.json()
    assert body["drafts"] == []
    assert body["failures"] == ["m1"]


def test_send_returns_message_id_on_success(client: TestClient) -> None:
    _override_oauth(can_send=True)
    adapter = MagicMock()
    adapter.send_reply.return_value = {"id": "sent-1"}
    _override_adapter(adapter)
    response = client.post(
        "/mail/send",
        json={
            "message_id": "<orig@m>",
            "thread_id": "t1",
            "to": "test@example.com",
            "subject": "Toplantı",
            "body": "Yarın uygunum.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sent_message_id"] == "sent-1"
    assert body["error"] is None
    adapter.send_reply.assert_called_once_with(
        to="test@example.com",
        subject="Toplantı",
        body="Yarın uygunum.",
        thread_id="t1",
        in_reply_to_message_id="<orig@m>",
    )


def test_send_returns_403_when_send_scope_missing(client: TestClient) -> None:
    _override_oauth(can_send=False)
    _override_adapter(MagicMock())
    response = client.post(
        "/mail/send",
        json={
            "message_id": "m",
            "thread_id": "t",
            "to": "x@y.com",
            "subject": "s",
            "body": "b",
        },
    )
    assert response.status_code == 403


def test_send_returns_401_when_disconnected(client: TestClient) -> None:
    _override_oauth_disconnected()
    _override_adapter(MagicMock())
    response = client.post(
        "/mail/send",
        json={
            "message_id": "m",
            "thread_id": "t",
            "to": "x@y.com",
            "subject": "s",
            "body": "b",
        },
    )
    assert response.status_code == 401


def test_send_returns_friendly_error_when_gmail_send_fails(client: TestClient) -> None:
    _override_oauth(can_send=True)
    adapter = MagicMock()
    adapter.send_reply.side_effect = GmailAdapterError("offline")
    _override_adapter(adapter)
    response = client.post(
        "/mail/send",
        json={
            "message_id": "m",
            "thread_id": "t",
            "to": "x@y.com",
            "subject": "s",
            "body": "b",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sent_message_id"] is None
    assert "gönderilemedi" in body["error"]["user_message"].lower()


def test_auth_status_reports_can_send_flag(client: TestClient) -> None:
    _override_oauth(can_send=True)
    response = client.get("/mail/auth-status")
    assert response.status_code == 200
    assert response.json()["can_send"] is True


def test_auth_status_reports_cannot_send_when_scope_missing(client: TestClient) -> None:
    _override_oauth(can_send=False)
    response = client.get("/mail/auth-status")
    assert response.status_code == 200
    assert response.json()["can_send"] is False
