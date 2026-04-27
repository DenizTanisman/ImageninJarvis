"""Application-scoped dependencies.

The dispatcher and OAuth service are lazily created on first request so
unit tests can override them via ``app.dependency_overrides[...]`` and
the test runner does not require real Google credentials.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.config import get_settings
from capabilities.calendar.adapter import CalendarAdapter
from capabilities.calendar.strategy import CalendarStrategy
from capabilities.document.drive_adapter import DriveAdapter
from capabilities.document.strategy import DocumentStrategy
from capabilities.gmail.adapter import GmailAdapter
from capabilities.gmail.classifier import EmailClassifier
from capabilities.gmail.draft import DraftGenerator
from capabilities.gmail.strategy import MailStrategy
from capabilities.translation.strategy import TranslationStrategy
from core.classifier import Classifier
from core.dispatcher import Dispatcher
from core.registry import default_registry
from services.auth_oauth import GoogleOAuthService
from services.cache_sqlite import EmailCache
from services.document_store import DocumentStore
from services.gemini_client import GeminiClient
from services.token_store import TokenStore


@lru_cache(maxsize=1)
def _build_default_dispatcher() -> Dispatcher:
    gemini = _build_gemini_client()
    # Eagerly register strategies the dispatcher needs to discover via
    # the classifier. Step 6.1: mail joins the eager set so voice / chat
    # can route "bugünün maillerini özetle" without first hitting the
    # /mail/summary shortcut.
    _ensure_registered(TranslationStrategy(gemini))
    _ensure_registered(_build_calendar_strategy())
    _ensure_registered(_build_mail_strategy())
    return Dispatcher(
        classifier=Classifier(gemini),
        registry=default_registry,
        gemini=gemini,
    )


@lru_cache(maxsize=1)
def _build_calendar_strategy() -> CalendarStrategy:
    return CalendarStrategy(oauth=_build_oauth_service())


def get_calendar_strategy() -> CalendarStrategy:
    strategy = _build_calendar_strategy()
    _ensure_registered(strategy)
    return strategy


def get_calendar_adapter_factory():
    """Return a callable that builds a CalendarAdapter from credentials.

    Tests override this with a factory that yields a mock adapter so the
    real google-api-python-client never gets touched.
    """
    return lambda creds: CalendarAdapter(creds)


@lru_cache(maxsize=1)
def _build_document_store() -> DocumentStore:
    return DocumentStore()


def get_document_store() -> DocumentStore:
    return _build_document_store()


@lru_cache(maxsize=1)
def _build_sandbox_root() -> Path:
    settings = get_settings()
    root = Path(settings.sandbox_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_sandbox_root() -> Path:
    return _build_sandbox_root()


@lru_cache(maxsize=1)
def _build_document_strategy() -> DocumentStrategy:
    return DocumentStrategy(
        store=_build_document_store(),
        gemini=_build_gemini_client(),
    )


def get_document_strategy() -> DocumentStrategy:
    strategy = _build_document_strategy()
    _ensure_registered(strategy)
    return strategy


def get_drive_adapter_factory():
    """Return a callable that builds a DriveAdapter from credentials.

    Tests override this with a factory that yields a mock adapter so
    google-api-python-client never gets instantiated for real."""
    return lambda creds: DriveAdapter(creds)


def _ensure_registered(strategy) -> None:
    if all(s.name != strategy.name for s in default_registry.all()):
        default_registry.register(strategy)


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


@lru_cache(maxsize=1)
def _build_gemini_client() -> GeminiClient:
    settings = get_settings()
    return GeminiClient(
        api_key=settings.gemini_api_key,
        model_name=settings.gemini_model,
    )


@lru_cache(maxsize=1)
def _build_email_cache() -> EmailCache:
    settings = get_settings()
    return EmailCache(settings.sqlite_path)


@lru_cache(maxsize=1)
def _build_mail_strategy() -> MailStrategy:
    return MailStrategy(
        oauth=_build_oauth_service(),
        classifier=EmailClassifier(_build_gemini_client()),
        cache=_build_email_cache(),
    )


def get_mail_strategy() -> MailStrategy:
    strategy = _build_mail_strategy()
    _ensure_registered(strategy)
    return strategy


@lru_cache(maxsize=1)
def _build_draft_generator() -> DraftGenerator:
    return DraftGenerator(_build_gemini_client())


def get_draft_generator() -> DraftGenerator:
    return _build_draft_generator()


def get_gmail_adapter_factory():
    """Return a callable that builds a GmailAdapter from credentials.

    Tests override this with a factory that yields a mock adapter so the
    real google-api-python-client never gets touched.
    """
    return lambda creds: GmailAdapter(creds)


@lru_cache(maxsize=1)
def _build_translation_strategy() -> TranslationStrategy:
    return TranslationStrategy(_build_gemini_client())


def get_translation_strategy() -> TranslationStrategy:
    strategy = _build_translation_strategy()
    _ensure_registered(strategy)
    return strategy
