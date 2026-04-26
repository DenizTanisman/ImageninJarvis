from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_mail_strategy, get_oauth_service
from app.main import app
from capabilities.gmail.strategy import MailStrategy
from core.result import Error, Success


@pytest.fixture()
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def _strategy_with_result(result):
    fake = MagicMock(spec=MailStrategy)
    fake.execute = AsyncMock(return_value=result)
    return fake


def test_summary_returns_success_payload(client: TestClient) -> None:
    fake = _strategy_with_result(
        Success(
            data={"categories": {"important": [], "dm": [], "promo": [], "other": []}, "total": 0, "needs_reply_count": 0},
            ui_type="MailCard",
            meta={"source": "live"},
        )
    )
    app.dependency_overrides[get_mail_strategy] = lambda: fake
    response = client.post(
        "/mail/summary",
        json={"range_kind": "daily", "after": "2026-04-24", "before": "2026-04-25"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["ui_type"] == "MailCard"
    fake.execute.assert_awaited_once()


def test_summary_returns_error_payload(client: TestClient) -> None:
    fake = _strategy_with_result(
        Error(message="not connected", user_message="Google bağlı değil")
    )
    app.dependency_overrides[get_mail_strategy] = lambda: fake
    response = client.post(
        "/mail/summary",
        json={"range_kind": "daily", "after": "2026-04-24", "before": "2026-04-25"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert "bağlı" in body["error"]["user_message"].lower()


def test_summary_validates_request_body(client: TestClient) -> None:
    app.dependency_overrides[get_mail_strategy] = lambda: _strategy_with_result(
        Success(data={}, ui_type="MailCard")
    )
    response = client.post(
        "/mail/summary",
        json={"range_kind": "daily", "after": "bad", "before": "2026-04-25"},
    )
    assert response.status_code == 422


def test_auth_status_returns_disconnected_when_no_token(client: TestClient) -> None:
    fake = MagicMock()
    fake.credentials_for.return_value = None
    app.dependency_overrides[get_oauth_service] = lambda: fake
    response = client.get("/mail/auth-status")
    assert response.status_code == 200
    assert response.json() == {"connected": False, "scopes": [], "can_send": False}


def test_auth_status_returns_connected_when_token_present(client: TestClient) -> None:
    fake = MagicMock()
    fake.credentials_for.return_value = MagicMock(
        scopes=["https://www.googleapis.com/auth/gmail.readonly"]
    )
    app.dependency_overrides[get_oauth_service] = lambda: fake
    response = client.get("/mail/auth-status")
    assert response.status_code == 200
    assert response.json()["connected"] is True
    assert response.json()["scopes"] == [
        "https://www.googleapis.com/auth/gmail.readonly"
    ]
