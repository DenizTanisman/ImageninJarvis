from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_calendar_strategy
from app.main import app
from capabilities.calendar.strategy import CalendarStrategy
from core.result import Error, Success


@pytest.fixture()
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def _override_strategy(returning: Success | Error) -> MagicMock:
    fake = MagicMock(spec=CalendarStrategy)
    fake.execute = AsyncMock(return_value=returning)
    app.dependency_overrides[get_calendar_strategy] = lambda: fake
    return fake


def test_calendar_list_forwards_to_strategy(client: TestClient) -> None:
    fake = _override_strategy(
        Success(data={"events": [], "days": 7}, ui_type="EventList")
    )
    response = client.post("/calendar", json={"action": "list", "days": 7})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["ui_type"] == "EventList"
    fake.execute.assert_awaited_once()
    payload = fake.execute.await_args.args[0]
    assert payload == {"action": "list", "days": 7}


def test_calendar_create_passes_full_payload(client: TestClient) -> None:
    fake = _override_strategy(
        Success(
            data={
                "id": "e1",
                "summary": "Sunum",
                "start": "2026-04-28T14:00:00+03:00",
                "end": "2026-04-28T15:00:00+03:00",
                "description": "",
                "html_link": "",
            },
            ui_type="CalendarEvent",
            meta={"action": "create"},
        )
    )
    response = client.post(
        "/calendar",
        json={
            "action": "create",
            "summary": "Sunum",
            "start": "2026-04-28T14:00:00+03:00",
            "end": "2026-04-28T15:00:00+03:00",
            "description": "",
        },
    )
    assert response.status_code == 200
    payload = fake.execute.await_args.args[0]
    assert payload["summary"] == "Sunum"
    assert payload["start"] == "2026-04-28T14:00:00+03:00"


def test_calendar_delete_passes_event_id(client: TestClient) -> None:
    fake = _override_strategy(
        Success(data={"event_id": "e1"}, ui_type="text", meta={"action": "delete"})
    )
    response = client.post("/calendar", json={"action": "delete", "event_id": "e1"})
    assert response.status_code == 200
    payload = fake.execute.await_args.args[0]
    assert payload == {"action": "delete", "event_id": "e1"}


def test_calendar_returns_friendly_error(client: TestClient) -> None:
    _override_strategy(
        Error(
            message="upstream",
            user_message="Takvim isteği başarısız oldu.",
            retry_after=10,
        )
    )
    response = client.post("/calendar", json={"action": "list"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["user_message"] == "Takvim isteği başarısız oldu."


def test_calendar_rejects_unknown_action(client: TestClient) -> None:
    response = client.post("/calendar", json={"action": "rsvp"})
    assert response.status_code == 422


def test_calendar_strips_unset_fields_from_payload(client: TestClient) -> None:
    """The frontend may submit only the fields the user actually changed —
    the route should drop None values so the strategy's "no fields" check
    fires correctly instead of seeing a payload full of nulls."""
    fake = _override_strategy(
        Success(
            data={"id": "e1", "summary": "x", "start": "", "end": "", "description": "", "html_link": ""},
            ui_type="CalendarEvent",
            meta={"action": "update"},
        )
    )
    response = client.post(
        "/calendar", json={"action": "update", "event_id": "e1", "summary": "x"}
    )
    assert response.status_code == 200
    payload = fake.execute.await_args.args[0]
    assert "start" not in payload
    assert "end" not in payload
    assert payload["summary"] == "x"
