"""Google OAuth helpers.

Builds the consent URL with a CSRF-protected state token, exchanges the
authorization code for tokens, and persists the resulting credentials
in the encrypted :class:`TokenStore`. The route layer (``app/routes/auth.py``)
wraps these helpers in HTTP endpoints; this module stays HTTP-agnostic
so we can reuse it from CLI utilities or background jobs later.
"""
from __future__ import annotations

import os

# Google honors `include_granted_scopes` and may return a token whose scope
# set is a *superset* of what we asked for (e.g. user already consented to
# calendar.events earlier on this OAuth client). oauthlib treats that as a
# scope mismatch and raises by default; relax it so we accept the broader
# grant and downgrade locally if needed. Must be set before importing Flow.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

import secrets  # noqa: E402
from collections.abc import Iterable  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from datetime import UTC, datetime  # noqa: E402

from google.auth.transport.requests import Request  # noqa: E402
from google.oauth2.credentials import Credentials  # noqa: E402
from google_auth_oauthlib.flow import Flow  # noqa: E402

from .token_store import TokenStore  # noqa: E402

# Capability scope groups. We pass the union to Google so the user
# consents once for everything Step 2 needs; future capabilities (calendar,
# drive) will trigger a re-consent the first time they're requested.
GMAIL_READONLY_SCOPES: tuple[str, ...] = (
    "https://www.googleapis.com/auth/gmail.readonly",
)
GMAIL_SEND_SCOPES: tuple[str, ...] = (
    "https://www.googleapis.com/auth/gmail.send",
)
GMAIL_FULL_SCOPES: tuple[str, ...] = GMAIL_READONLY_SCOPES + GMAIL_SEND_SCOPES
DEFAULT_USER_ID = "default"


def has_required_scopes(granted: Iterable[str], required: Iterable[str]) -> bool:
    granted_set = set(granted)
    return all(req in granted_set for req in required)


@dataclass(frozen=True)
class AuthorizationStart:
    url: str
    state: str
    code_verifier: str


@dataclass(frozen=True)
class CallbackResult:
    user_id: str
    granted_scopes: tuple[str, ...]


class OAuthError(RuntimeError):
    pass


class GoogleOAuthService:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        token_store: TokenStore,
        scopes: Iterable[str] = GMAIL_FULL_SCOPES,
    ) -> None:
        if not client_id or not client_secret:
            raise OAuthError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required")
        if not redirect_uri:
            raise OAuthError("GOOGLE_REDIRECT_URI is required")
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._scopes = tuple(scopes)
        self._tokens = token_store

    def _client_config(self) -> dict:
        return {
            "web": {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self._redirect_uri],
            }
        }

    def build_authorization(self) -> AuthorizationStart:
        flow = Flow.from_client_config(
            self._client_config(),
            scopes=list(self._scopes),
            redirect_uri=self._redirect_uri,
        )
        # Force PKCE: pre-set the verifier so we can persist it across the
        # request/callback boundary (the Flow instance is otherwise lost).
        verifier = secrets.token_urlsafe(64)
        flow.code_verifier = verifier
        state = secrets.token_urlsafe(32)
        url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state,
        )
        return AuthorizationStart(url=url, state=state, code_verifier=verifier)

    def exchange_code(
        self,
        *,
        code: str,
        code_verifier: str,
        user_id: str = DEFAULT_USER_ID,
    ) -> CallbackResult:
        flow = Flow.from_client_config(
            self._client_config(),
            scopes=list(self._scopes),
            redirect_uri=self._redirect_uri,
        )
        flow.code_verifier = code_verifier
        try:
            flow.fetch_token(code=code)
        except Exception as exc:  # noqa: BLE001 — surface as OAuthError
            raise OAuthError(f"Token exchange failed: {exc}") from exc

        credentials = flow.credentials
        if not credentials.refresh_token:
            raise OAuthError(
                "Google did not return a refresh token. Revoke prior consent and retry."
            )
        granted = tuple(credentials.scopes or self._scopes)
        self._tokens.save(
            user_id,
            refresh_token=credentials.refresh_token,
            access_token=credentials.token or "",
            expiry_iso=_iso(credentials.expiry),
            scopes=granted,
        )
        return CallbackResult(user_id=user_id, granted_scopes=granted)

    def credentials_for(self, user_id: str = DEFAULT_USER_ID) -> Credentials | None:
        stored = self._tokens.load(user_id)
        if stored is None:
            return None
        creds = Credentials(
            token=stored.access_token or None,
            refresh_token=stored.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self._client_id,
            client_secret=self._client_secret,
            scopes=list(stored.scopes),
        )
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:  # noqa: BLE001
                raise OAuthError(f"Refresh failed: {exc}") from exc
            self._tokens.save(
                user_id,
                refresh_token=creds.refresh_token,
                access_token=creds.token or "",
                expiry_iso=_iso(creds.expiry),
                scopes=stored.scopes,
            )
        return creds


def _iso(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()
