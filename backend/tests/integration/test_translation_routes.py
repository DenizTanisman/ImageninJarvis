from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_translation_strategy
from app.main import app
from capabilities.translation.strategy import TranslationStrategy
from core.result import Error, Success


@pytest.fixture()
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def _override_strategy(returning: Success | Error) -> MagicMock:
    fake = MagicMock(spec=TranslationStrategy)
    fake.execute = AsyncMock(return_value=returning)
    app.dependency_overrides[get_translation_strategy] = lambda: fake
    return fake


def test_translate_returns_success_payload(client: TestClient) -> None:
    fake = _override_strategy(
        Success(
            data={
                "source_text": "merhaba",
                "translated_text": "hello",
                "source_lang": "tr",
                "target_lang": "en",
            },
            ui_type="TranslationCard",
        )
    )
    response = client.post(
        "/translation",
        json={"text": "merhaba", "source": "tr", "target": "en"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["ui_type"] == "TranslationCard"
    assert body["data"]["translated_text"] == "hello"
    fake.execute.assert_awaited_once()
    payload = fake.execute.await_args.args[0]
    assert payload == {"text": "merhaba", "source": "tr", "target": "en"}


def test_translate_returns_friendly_error(client: TestClient) -> None:
    _override_strategy(
        Error(
            message="upstream",
            user_message="Çeviri servisi yanıt vermiyor.",
            retry_after=15,
        )
    )
    response = client.post(
        "/translation",
        json={"text": "hi", "source": "auto", "target": "tr"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["user_message"] == "Çeviri servisi yanıt vermiyor."
    assert body["error"]["retry_after"] == 15


def test_translate_rejects_missing_target(client: TestClient) -> None:
    response = client.post(
        "/translation",
        json={"text": "hi", "source": "en"},
    )
    assert response.status_code == 422


def test_translate_rejects_empty_text(client: TestClient) -> None:
    response = client.post(
        "/translation",
        json={"text": "", "target": "en"},
    )
    assert response.status_code == 422


def test_translate_defaults_source_to_auto(client: TestClient) -> None:
    fake = _override_strategy(
        Success(
            data={
                "source_text": "hi",
                "translated_text": "merhaba",
                "source_lang": "auto",
                "target_lang": "tr",
            },
            ui_type="TranslationCard",
        )
    )
    response = client.post("/translation", json={"text": "hi", "target": "tr"})
    assert response.status_code == 200
    payload = fake.execute.await_args.args[0]
    assert payload["source"] == "auto"
