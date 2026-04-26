from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from services.auth_oauth import (
    ALL_SCOPES,
    CALENDAR_SCOPES,
    GMAIL_FULL_SCOPES,
    GMAIL_READONLY_SCOPES,
    GoogleOAuthService,
    OAuthError,
    has_required_scopes,
)
from services.token_store import TokenStore


@pytest.fixture()
def store(tmp_path):
    return TokenStore(tmp_path / "tokens.db", Fernet.generate_key().decode())


def _service(store: TokenStore) -> GoogleOAuthService:
    return GoogleOAuthService(
        client_id="cid",
        client_secret="csec",
        redirect_uri="http://localhost:8000/auth/google/callback",
        token_store=store,
    )


def test_constructor_requires_client_credentials(store: TokenStore) -> None:
    with pytest.raises(OAuthError):
        GoogleOAuthService(
            client_id="",
            client_secret="",
            redirect_uri="http://x",
            token_store=store,
        )


def test_constructor_requires_redirect(store: TokenStore) -> None:
    with pytest.raises(OAuthError):
        GoogleOAuthService(
            client_id="cid",
            client_secret="csec",
            redirect_uri="",
            token_store=store,
        )


def test_build_authorization_returns_state_and_url(store: TokenStore) -> None:
    service = _service(store)
    auth = service.build_authorization()
    assert auth.url.startswith("https://accounts.google.com/")
    assert auth.state and len(auth.state) >= 32
    assert auth.code_verifier and len(auth.code_verifier) >= 43
    assert "client_id=cid" in auth.url
    assert "scope=" in auth.url
    assert "access_type=offline" in auth.url
    assert "code_challenge=" in auth.url
    assert "code_challenge_method=S256" in auth.url


def test_exchange_code_persists_token(store: TokenStore) -> None:
    service = _service(store)
    fake_credentials = SimpleNamespace(
        token="access-1",
        refresh_token="refresh-1",
        expiry=None,
        scopes=list(GMAIL_READONLY_SCOPES),
    )
    fake_flow = MagicMock()
    fake_flow.fetch_token = MagicMock(return_value=None)
    fake_flow.credentials = fake_credentials

    with patch(
        "services.auth_oauth.Flow.from_client_config", return_value=fake_flow
    ) as flow_factory:
        result = service.exchange_code(code="auth-code", code_verifier="verifier-1")

    flow_factory.assert_called()
    fake_flow.fetch_token.assert_called_once_with(code="auth-code")
    assert fake_flow.code_verifier == "verifier-1"

    stored = store.load("default")
    assert stored is not None
    assert stored.refresh_token == "refresh-1"
    assert stored.access_token == "access-1"
    assert stored.scopes == GMAIL_READONLY_SCOPES
    assert result.granted_scopes == GMAIL_READONLY_SCOPES


def test_exchange_code_raises_when_no_refresh_token(store: TokenStore) -> None:
    service = _service(store)
    fake_credentials = SimpleNamespace(
        token="access",
        refresh_token=None,
        expiry=None,
        scopes=list(GMAIL_READONLY_SCOPES),
    )
    fake_flow = MagicMock()
    fake_flow.fetch_token = MagicMock(return_value=None)
    fake_flow.credentials = fake_credentials
    with patch("services.auth_oauth.Flow.from_client_config", return_value=fake_flow):
        with pytest.raises(OAuthError):
            service.exchange_code(code="auth-code", code_verifier="v")


def test_exchange_code_wraps_fetch_failures(store: TokenStore) -> None:
    service = _service(store)
    fake_flow = MagicMock()
    fake_flow.fetch_token = MagicMock(side_effect=RuntimeError("network"))
    with patch("services.auth_oauth.Flow.from_client_config", return_value=fake_flow):
        with pytest.raises(OAuthError):
            service.exchange_code(code="bad", code_verifier="v")


def test_credentials_for_returns_none_when_unconnected(store: TokenStore) -> None:
    service = _service(store)
    assert service.credentials_for() is None


def test_credentials_for_returns_credentials_when_stored(store: TokenStore) -> None:
    store.save(
        "default",
        refresh_token="r",
        access_token="a",
        expiry_iso="2099-01-01T00:00:00+00:00",
        scopes=GMAIL_READONLY_SCOPES,
    )
    service = _service(store)
    creds = service.credentials_for()
    assert creds is not None
    assert creds.refresh_token == "r"
    assert creds.token == "a"


def test_default_scopes_include_gmail_and_calendar() -> None:
    """Step 4.1: a fresh OAuth grant must request calendar.events alongside
    gmail so the user only sees one consent screen for everything."""
    assert set(GMAIL_FULL_SCOPES).issubset(set(ALL_SCOPES))
    assert set(CALENDAR_SCOPES).issubset(set(ALL_SCOPES))


def test_has_required_scopes_recognizes_calendar_subset() -> None:
    granted = list(GMAIL_FULL_SCOPES) + list(CALENDAR_SCOPES)
    assert has_required_scopes(granted, CALENDAR_SCOPES)
    assert not has_required_scopes(GMAIL_READONLY_SCOPES, CALENDAR_SCOPES)
