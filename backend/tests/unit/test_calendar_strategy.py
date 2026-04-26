from unittest.mock import MagicMock

import pytest

from capabilities.calendar.adapter import CalendarAdapterError
from capabilities.calendar.models import CalendarEvent
from capabilities.calendar.strategy import CalendarStrategy
from core.result import Error, Success
from services.auth_oauth import CALENDAR_SCOPES


def _oauth(*, creds=None, raises: Exception | None = None) -> MagicMock:
    fake = MagicMock()
    if raises is not None:
        fake.credentials_for.side_effect = raises
    else:
        fake.credentials_for.return_value = creds
    return fake


def _creds_with_calendar() -> MagicMock:
    return MagicMock(scopes=list(CALENDAR_SCOPES))


def _strategy(adapter: MagicMock, *, oauth: MagicMock | None = None) -> CalendarStrategy:
    return CalendarStrategy(
        oauth=oauth or _oauth(creds=_creds_with_calendar()),
        adapter_factory=lambda _creds: adapter,
    )


def _event(**overrides) -> CalendarEvent:
    base = {
        "id": "e1",
        "summary": "Sunum",
        "start": "2026-04-28T14:00:00+03:00",
        "end": "2026-04-28T15:00:00+03:00",
        "description": "Q2 sprint",
        "html_link": "https://calendar.google.com/event?eid=x",
    }
    base.update(overrides)
    return CalendarEvent(**base)


# ---------- routing / auth ----------


@pytest.mark.asyncio
async def test_unknown_action_returns_error() -> None:
    strategy = _strategy(MagicMock())
    result = await strategy.execute({"action": "rsvp"})
    assert isinstance(result, Error)
    assert "anlayamadım" in result.user_message.lower()


@pytest.mark.asyncio
async def test_returns_error_when_not_connected() -> None:
    strategy = CalendarStrategy(
        oauth=_oauth(creds=None),
        adapter_factory=lambda _creds: MagicMock(),
    )
    result = await strategy.execute({"action": "list"})
    assert isinstance(result, Error)
    assert "bağlı değilsin" in result.user_message.lower()


@pytest.mark.asyncio
async def test_returns_error_when_calendar_scope_missing() -> None:
    creds = MagicMock(scopes=["https://www.googleapis.com/auth/gmail.readonly"])
    strategy = CalendarStrategy(
        oauth=_oauth(creds=creds),
        adapter_factory=lambda _c: MagicMock(),
    )
    result = await strategy.execute({"action": "list"})
    assert isinstance(result, Error)
    assert "takvim izni" in result.user_message.lower()


@pytest.mark.asyncio
async def test_returns_error_when_credential_refresh_raises() -> None:
    strategy = CalendarStrategy(
        oauth=_oauth(raises=RuntimeError("refresh boom")),
        adapter_factory=lambda _c: MagicMock(),
    )
    result = await strategy.execute({"action": "list"})
    assert isinstance(result, Error)
    assert "yenilenemedi" in result.user_message.lower()


# ---------- list ----------


@pytest.mark.asyncio
async def test_list_returns_serialized_events() -> None:
    adapter = MagicMock()
    adapter.list_events.return_value = [_event(id="e1"), _event(id="e2")]
    strategy = _strategy(adapter)
    result = await strategy.execute({"action": "list", "days": 7})
    assert isinstance(result, Success)
    assert result.ui_type == "EventList"
    assert len(result.data["events"]) == 2
    assert result.data["events"][0]["id"] == "e1"
    assert result.data["days"] == 7


@pytest.mark.asyncio
async def test_list_defaults_days_when_missing() -> None:
    adapter = MagicMock()
    adapter.list_events.return_value = []
    strategy = _strategy(adapter)
    result = await strategy.execute({"action": "list"})
    assert isinstance(result, Success)
    adapter.list_events.assert_called_once()
    assert adapter.list_events.call_args.kwargs["days"] == 7


# ---------- create ----------


@pytest.mark.asyncio
async def test_create_returns_event_on_success() -> None:
    adapter = MagicMock()
    adapter.create_event.return_value = _event(id="new-1")
    strategy = _strategy(adapter)
    result = await strategy.execute(
        {
            "action": "create",
            "summary": "Sunum",
            "start": "2026-04-28T14:00:00+03:00",
            "end": "2026-04-28T15:00:00+03:00",
            "description": "Q2 sprint",
        }
    )
    assert isinstance(result, Success)
    assert result.ui_type == "CalendarEvent"
    assert result.data["id"] == "new-1"
    assert result.meta == {"action": "create"}


@pytest.mark.asyncio
async def test_create_rejects_missing_fields() -> None:
    strategy = _strategy(MagicMock())
    result = await strategy.execute({"action": "create"})
    assert isinstance(result, Error)
    assert "başlık" in result.user_message.lower()


@pytest.mark.asyncio
async def test_create_rejects_end_before_start() -> None:
    strategy = _strategy(MagicMock())
    result = await strategy.execute(
        {
            "action": "create",
            "summary": "x",
            "start": "2026-04-28T15:00:00+03:00",
            "end": "2026-04-28T14:00:00+03:00",
        }
    )
    assert isinstance(result, Error)


# ---------- update ----------


@pytest.mark.asyncio
async def test_update_passes_only_set_fields() -> None:
    adapter = MagicMock()
    adapter.update_event.return_value = _event(id="e1", summary="Yeni")
    strategy = _strategy(adapter)
    result = await strategy.execute(
        {"action": "update", "event_id": "e1", "summary": "Yeni"}
    )
    assert isinstance(result, Success)
    adapter.update_event.assert_called_once_with("e1", summary="Yeni")


@pytest.mark.asyncio
async def test_update_rejects_missing_id() -> None:
    strategy = _strategy(MagicMock())
    result = await strategy.execute({"action": "update", "summary": "x"})
    assert isinstance(result, Error)


@pytest.mark.asyncio
async def test_update_rejects_no_fields() -> None:
    strategy = _strategy(MagicMock())
    result = await strategy.execute({"action": "update", "event_id": "e1"})
    assert isinstance(result, Error)
    assert "alan" in result.user_message.lower()


@pytest.mark.asyncio
async def test_update_rejects_end_before_start() -> None:
    strategy = _strategy(MagicMock())
    result = await strategy.execute(
        {
            "action": "update",
            "event_id": "e1",
            "start": "2026-04-29T15:00:00+03:00",
            "end": "2026-04-29T14:00:00+03:00",
        }
    )
    assert isinstance(result, Error)


# ---------- delete ----------


@pytest.mark.asyncio
async def test_delete_returns_event_id_on_success() -> None:
    adapter = MagicMock()
    strategy = _strategy(adapter)
    result = await strategy.execute({"action": "delete", "event_id": "e1"})
    assert isinstance(result, Success)
    assert result.data == {"event_id": "e1"}
    assert result.meta == {"action": "delete"}
    adapter.delete_event.assert_called_once_with("e1")


@pytest.mark.asyncio
async def test_delete_rejects_missing_id() -> None:
    strategy = _strategy(MagicMock())
    result = await strategy.execute({"action": "delete"})
    assert isinstance(result, Error)


# ---------- adapter failures wrapped ----------


@pytest.mark.asyncio
async def test_adapter_error_surfaces_as_friendly_error() -> None:
    adapter = MagicMock()
    adapter.list_events.side_effect = CalendarAdapterError("offline")
    strategy = _strategy(adapter)
    result = await strategy.execute({"action": "list"})
    assert isinstance(result, Error)
    assert result.retry_after == 10


# ---------- contract ----------


def test_can_handle_only_calendar_intent() -> None:
    strategy = _strategy(MagicMock())
    assert strategy.can_handle({"type": "calendar"})
    assert not strategy.can_handle({"type": "mail"})


def test_render_hint_is_event_list() -> None:
    strategy = _strategy(MagicMock())
    assert strategy.render_hint() == "EventList"
