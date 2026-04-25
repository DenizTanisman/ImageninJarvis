"""Application-scoped dependencies.

The dispatcher is lazily created on first request so unit tests can
override it via ``app.dependency_overrides[get_dispatcher] = ...`` and
the test runner does not require a real ``GEMINI_API_KEY``.
"""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from core.classifier import Classifier
from core.dispatcher import Dispatcher
from core.registry import default_registry
from services.gemini_client import GeminiClient


@lru_cache(maxsize=1)
def _build_default_dispatcher() -> Dispatcher:
    settings = get_settings()
    gemini = GeminiClient(api_key=settings.gemini_api_key)
    return Dispatcher(
        classifier=Classifier(),
        registry=default_registry,
        gemini=gemini,
    )


def get_dispatcher() -> Dispatcher:
    """FastAPI dependency: returns the singleton Dispatcher."""
    return _build_default_dispatcher()
