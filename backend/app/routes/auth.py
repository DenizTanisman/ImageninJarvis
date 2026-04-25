"""Google OAuth start + callback endpoints.

A simple in-memory ``state`` registry is enough for the single-user dev
setup; if we ever support multiple concurrent OAuth flows we can move
this to a short-lived Redis/SQLite table.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies import get_oauth_service
from services.auth_oauth import GoogleOAuthService, OAuthError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/google", tags=["auth"])

OAuthDep = Annotated[GoogleOAuthService, Depends(get_oauth_service)]

# State registry maps state token → PKCE code_verifier captured at /start.
# We need both halves (state for CSRF, verifier to satisfy Google's PKCE
# challenge) on the callback side, so they live together in one record.
_pending_states: dict[str, str] = {}


@router.get("/start")
async def start(oauth: OAuthDep) -> RedirectResponse:
    try:
        authorization = oauth.build_authorization()
    except OAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    _pending_states[authorization.state] = authorization.code_verifier
    return RedirectResponse(authorization.url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/callback")
async def callback(
    oauth: OAuthDep,
    state: str = Query(...),
    code: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> HTMLResponse:
    verifier = _pending_states.pop(state, None)
    if verifier is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state — possible CSRF.",
        )

    if error or not code:
        logger.warning("OAuth callback received error=%r code=%r", error, code)
        return HTMLResponse(
            _result_page(
                title="Bağlantı iptal edildi",
                body=f"Google bağlantısı tamamlanamadı ({error or 'no code'}).",
            ),
            status_code=400,
        )

    try:
        result = oauth.exchange_code(code=code, code_verifier=verifier)
    except OAuthError as exc:
        logger.error("OAuth callback failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return HTMLResponse(
        _result_page(
            title="Google bağlantısı başarılı",
            body=(
                f"<code>{result.user_id}</code> için scope'lar kaydedildi: "
                f"{', '.join(result.granted_scopes)}"
            ),
            redirect_to="http://localhost:5173/chat",
        )
    )


def _result_page(*, title: str, body: str, redirect_to: str | None = None) -> str:
    redirect_meta = (
        f'<meta http-equiv="refresh" content="2;url={redirect_to}">'
        if redirect_to
        else ""
    )
    redirect_note = (
        f'<p style="color:#94a3b8;margin-top:2rem;font-size:0.9rem;">'
        f'Birkaç saniye içinde Jarvis arayüzüne yönlendiriliyorsun.</p>'
        if redirect_to
        else '<p style="color:#94a3b8;margin-top:2rem;font-size:0.9rem;">'
             "Bu sekmeyi kapatabilirsin, Jarvis arayüzüne dön.</p>"
    )
    return f"""
<!doctype html>
<html lang="tr">
<head><meta charset="utf-8"><title>{title}</title>{redirect_meta}</head>
<body style="font-family:system-ui;background:#0f172a;color:#e2e8f0;padding:2rem;">
  <h1 style="margin-bottom:1rem;">{title}</h1>
  <p>{body}</p>
  {redirect_note}
</body>
</html>
""".strip()
