from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_dispatcher
from app.main import app
from core.classifier import Classifier
from core.dispatcher import Dispatcher
from core.registry import CapabilityRegistry
from services.gemini_client import GeminiClient


def _dispatcher_with_text(text: str) -> Dispatcher:
    model = AsyncMock()
    model.generate_content_async.return_value = SimpleNamespace(text=text)
    gemini = GeminiClient(model=model, max_concurrent=2, max_attempts=1)
    return Dispatcher(
        classifier=Classifier(),
        registry=CapabilityRegistry(),
        gemini=gemini,
    )


def _dispatcher_with_failure() -> Dispatcher:
    model = AsyncMock()
    model.generate_content_async.side_effect = RuntimeError("offline")
    gemini = GeminiClient(model=model, max_concurrent=2, max_attempts=1)
    return Dispatcher(
        classifier=Classifier(),
        registry=CapabilityRegistry(),
        gemini=gemini,
    )


@pytest.fixture()
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_post_chat_returns_success_payload(client: TestClient) -> None:
    app.dependency_overrides[get_dispatcher] = lambda: _dispatcher_with_text(
        "merhaba!"
    )
    response = client.post("/chat", json={"text": "Selam"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["ui_type"] == "text"
    assert body["data"] == "merhaba!"
    assert body["meta"] == {"source": "fallback"}
    assert body["error"] is None


def test_post_chat_returns_error_payload_when_gemini_unreachable(client: TestClient) -> None:
    app.dependency_overrides[get_dispatcher] = lambda: _dispatcher_with_failure()
    response = client.post("/chat", json={"text": "Selam"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["retry_after"] == 10
    assert "tekrar" in body["error"]["user_message"].lower()


def test_post_chat_rejects_empty_text(client: TestClient) -> None:
    app.dependency_overrides[get_dispatcher] = lambda: _dispatcher_with_text("ignored")
    response = client.post("/chat", json={"text": ""})
    assert response.status_code == 422


def test_post_chat_rejects_oversize_text(client: TestClient) -> None:
    app.dependency_overrides[get_dispatcher] = lambda: _dispatcher_with_text("ignored")
    big = "a" * 4001
    response = client.post("/chat", json={"text": big})
    assert response.status_code == 422


def test_post_chat_returns_friendly_error_for_whitespace_only(client: TestClient) -> None:
    app.dependency_overrides[get_dispatcher] = lambda: _dispatcher_with_text("ignored")
    response = client.post("/chat", json={"text": "    "})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert "yazmamışsın" in body["error"]["user_message"]
