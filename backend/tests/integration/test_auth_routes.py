from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_oauth_service
from app.main import app
from app.routes import auth as auth_routes
from services.auth_oauth import (
    GMAIL_READONLY_SCOPES,
    AuthorizationStart,
    CallbackResult,
    OAuthError,
)


@pytest.fixture()
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()
    auth_routes._pending_states.clear()


def _override(service: MagicMock) -> None:
    app.dependency_overrides[get_oauth_service] = lambda: service


def test_start_redirects_to_consent_url(client: TestClient) -> None:
    fake = MagicMock()
    fake.build_authorization.return_value = AuthorizationStart(
        url="https://accounts.google.com/o/oauth2/auth?xyz",
        state="state-token",
        code_verifier="verifier-token",
    )
    _override(fake)
    response = client.get("/auth/google/start", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"].startswith("https://accounts.google.com/")
    assert auth_routes._pending_states.get("state-token") == "verifier-token"


def test_start_returns_503_when_oauth_misconfigured(client: TestClient) -> None:
    fake = MagicMock()
    fake.build_authorization.side_effect = OAuthError("missing client id")
    _override(fake)
    response = client.get("/auth/google/start", follow_redirects=False)
    assert response.status_code == 503


def test_callback_rejects_unknown_state(client: TestClient) -> None:
    _override(MagicMock())
    response = client.get(
        "/auth/google/callback",
        params={"state": "ghost", "code": "abc"},
    )
    assert response.status_code == 400


def test_callback_with_error_param_returns_400_html(client: TestClient) -> None:
    fake = MagicMock()
    _override(fake)
    auth_routes._pending_states["ok-state"] = "verifier-1"
    response = client.get(
        "/auth/google/callback",
        params={"state": "ok-state", "error": "access_denied"},
    )
    assert response.status_code == 400
    assert "iptal" in response.text.lower()
    fake.exchange_code.assert_not_called()
    assert "ok-state" not in auth_routes._pending_states


def test_callback_success_exchanges_code_and_renders_page(client: TestClient) -> None:
    fake = MagicMock()
    fake.exchange_code.return_value = CallbackResult(
        user_id="default", granted_scopes=GMAIL_READONLY_SCOPES
    )
    _override(fake)
    auth_routes._pending_states["ok-state-2"] = "verifier-2"
    response = client.get(
        "/auth/google/callback",
        params={"state": "ok-state-2", "code": "the-code"},
    )
    assert response.status_code == 200
    assert "başarılı" in response.text.lower()
    fake.exchange_code.assert_called_once_with(
        code="the-code", code_verifier="verifier-2"
    )
    assert "ok-state-2" not in auth_routes._pending_states


def test_callback_translates_oauth_errors_to_502(client: TestClient) -> None:
    fake = MagicMock()
    fake.exchange_code.side_effect = OAuthError("bad code")
    _override(fake)
    auth_routes._pending_states["ok-state-3"] = "verifier-3"
    response = client.get(
        "/auth/google/callback",
        params={"state": "ok-state-3", "code": "bad"},
    )
    assert response.status_code == 502
