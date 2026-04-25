"""Application-scoped dependencies.

The dispatcher and OAuth service are lazily created on first request so
unit tests can override them via ``app.dependency_overrides[...]`` and
the test runner does not require real Google credentials.
"""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from core.classifier import Classifier
from core.dispatcher import Dispatcher
from core.registry import default_registry
from services.auth_oauth import GoogleOAuthService
from services.gemini_client import GeminiClient
from services.token_store import TokenStore


@lru_cache(maxsize=1)
def _build_default_dispatcher() -> Dispatcher:
    settings = get_settings()
    gemini = GeminiClient(
        api_key=settings.gemini_api_key,
        model_name=settings.gemini_model,
    )
    return Dispatcher(
        classifier=Classifier(),
        registry=default_registry,
        gemini=gemini,
    )


def get_dispatcher() -> Dispatcher:
    """FastAPI dependency: returns the singleton Dispatcher."""
    return _build_default_dispatcher()


@lru_cache(maxsize=1)
def _build_token_store() -> TokenStore:
    settings = get_settings()
    return TokenStore(settings.sqlite_path, settings.encryption_key)


@lru_cache(maxsize=1)
def _build_oauth_service() -> GoogleOAuthService:
    settings = get_settings()
    return GoogleOAuthService(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
        token_store=_build_token_store(),
    )


def get_token_store() -> TokenStore:
    return _build_token_store()


def get_oauth_service() -> GoogleOAuthService:
    return _build_oauth_service()
