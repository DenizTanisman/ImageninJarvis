from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_document_strategy
from app.main import app
from capabilities.document.strategy import DocumentStrategy
from core.result import Error, Success


@pytest.fixture()
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def _override_strategy(returning: Success | Error) -> MagicMock:
    fake = MagicMock(spec=DocumentStrategy)
    fake.execute = AsyncMock(return_value=returning)
    app.dependency_overrides[get_document_strategy] = lambda: fake
    return fake


def test_document_ask_forwards_to_strategy(client: TestClient) -> None:
    fake = _override_strategy(
        Success(
            data={
                "doc_id": "abc",
                "question": "ne var?",
                "answer": "Belgede X yazıyor.",
                "chunks_used": 3,
                "total_chunks": 5,
            },
            ui_type="DocumentAnswer",
        )
    )
    response = client.post(
        "/document",
        json={"action": "ask", "doc_id": "abc", "question": "ne var?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["answer"] == "Belgede X yazıyor."
    payload = fake.execute.await_args.args[0]
    assert payload["doc_id"] == "abc"
    assert payload["question"] == "ne var?"


def test_document_returns_friendly_error(client: TestClient) -> None:
    _override_strategy(
        Error(
            message="upstream",
            user_message="Belge cevabı üretilemedi.",
            retry_after=15,
        )
    )
    response = client.post(
        "/document",
        json={"action": "ask", "doc_id": "abc", "question": "q"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["retry_after"] == 15


def test_document_rejects_empty_question(client: TestClient) -> None:
    response = client.post(
        "/document", json={"action": "ask", "doc_id": "abc", "question": ""}
    )
    assert response.status_code == 422


def test_document_rejects_missing_doc_id(client: TestClient) -> None:
    response = client.post(
        "/document", json={"action": "ask", "question": "q"}
    )
    assert response.status_code == 422


def test_document_rejects_unknown_action(client: TestClient) -> None:
    response = client.post(
        "/document",
        json={"action": "summarize", "doc_id": "abc", "question": "q"},
    )
    assert response.status_code == 422
