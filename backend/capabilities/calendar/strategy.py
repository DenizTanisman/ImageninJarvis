"""CalendarStrategy — dispatch table for the four event actions.

Payload shape:
    {"action": "list" | "create" | "update" | "delete", ...action-specific fields}

The strategy never raises: every failure (no creds, missing scope,
adapter error, validation) becomes an :class:`Error` so the dispatcher /
route layer can hand the user a sanitized message.
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from core.base_strategy import CapabilityStrategy
from core.result import Error, Result, Success
from services.auth_oauth import (
    CALENDAR_SCOPES,
    GoogleOAuthService,
    has_required_scopes,
)

from .adapter import (
    DEFAULT_DAYS_AHEAD,
    CalendarAdapter,
    CalendarAdapterError,
)
from .models import CalendarEvent

logger = logging.getLogger(__name__)

VALID_ACTIONS: tuple[str, ...] = ("list", "create", "update", "delete")


class CalendarStrategy(CapabilityStrategy):
    name = "calendar"
    intent_keys = ("calendar", "etkinlik", "takvim", "event")

    def __init__(
        self,
        *,
        oauth: GoogleOAuthService,
        adapter_factory=None,
    ) -> None:
        self._oauth = oauth
        self._adapter_factory = adapter_factory or (lambda creds: CalendarAdapter(creds))

    def can_handle(self, intent: dict[str, Any]) -> bool:
        return intent.get("type") == "calendar"

    async def execute(self, payload: dict[str, Any]) -> Result:
        action = payload.get("action")
        if action not in VALID_ACTIONS:
            return Error(
                message=f"unknown action: {action!r}",
                user_message="Bu takvim isteğini anlayamadım.",
                user_notify=True,
                log_level="info",
            )

        creds_or_error = self._resolve_credentials()
        if isinstance(creds_or_error, Error):
            return creds_or_error
        adapter = self._adapter_factory(creds_or_error)

        try:
            if action == "list":
                return self._list(adapter, payload)
            if action == "create":
                return self._create(adapter, payload)
            if action == "update":
                return self._update(adapter, payload)
            return self._delete(adapter, payload)
        except CalendarAdapterError as exc:
            logger.error("Calendar %s failed: %s", action, exc)
            return Error(
                message=str(exc),
                user_message="Takvim isteği başarısız oldu, biraz sonra tekrar dener misin?",
                retry_after=10,
            )

    def render_hint(self) -> str:
        return "EventList"

    # ---------- internals ----------

    def _resolve_credentials(self) -> Any:
        """Return live ``Credentials`` or an ``Error`` ready to surface."""
        try:
            creds = self._oauth.credentials_for()
        except Exception as exc:  # noqa: BLE001
            logger.error("Calendar credential refresh failed: %s", exc)
            return Error(
                message=str(exc),
                user_message="Google bağlantın yenilenemedi, tekrar bağlan.",
            )
        if creds is None:
            return Error(
                message="not connected",
                user_message="Google'a bağlı değilsin. Önce takvim erişimi için bağlan.",
                user_notify=True,
                log_level="info",
            )
        if not has_required_scopes(creds.scopes or [], CALENDAR_SCOPES):
            return Error(
                message="missing calendar scope",
                user_message=(
                    "Takvim izni yok. Google'a tekrar bağlanıp takvim "
                    "iznini de ver."
                ),
                user_notify=True,
                log_level="info",
            )
        return creds

    def _list(self, adapter: CalendarAdapter, payload: dict[str, Any]) -> Result:
        days = int(payload.get("days") or DEFAULT_DAYS_AHEAD)
        events = adapter.list_events(days=days)
        return Success(
            data={"events": [asdict(e) for e in events], "days": days},
            ui_type="EventList",
        )

    def _create(self, adapter: CalendarAdapter, payload: dict[str, Any]) -> Result:
        summary = (payload.get("summary") or "").strip()
        start = (payload.get("start") or "").strip()
        end = (payload.get("end") or "").strip()
        description = (payload.get("description") or "").strip()
        missing = _missing_fields(summary=summary, start=start, end=end)
        if missing:
            return Error(
                message=f"missing fields: {missing}",
                user_message=f"Şu alanlar eksik: {', '.join(missing)}.",
                user_notify=True,
                log_level="info",
            )
        if start >= end:
            return Error(
                message="start>=end",
                user_message="Bitiş zamanı başlangıçtan sonra olmalı.",
                user_notify=True,
                log_level="info",
            )
        event = adapter.create_event(
            summary=summary, start=start, end=end, description=description
        )
        return Success(
            data=_event_payload(event),
            ui_type="CalendarEvent",
            meta={"action": "create"},
        )

    def _update(self, adapter: CalendarAdapter, payload: dict[str, Any]) -> Result:
        event_id = (payload.get("event_id") or "").strip()
        if not event_id:
            return Error(
                message="missing event_id",
                user_message="Hangi etkinlik düzenleniyor?",
                user_notify=True,
                log_level="info",
            )
        kwargs: dict[str, Any] = {}
        if "summary" in payload and payload["summary"] is not None:
            kwargs["summary"] = payload["summary"]
        if "description" in payload and payload["description"] is not None:
            kwargs["description"] = payload["description"]
        if "start" in payload and payload["start"]:
            kwargs["start"] = payload["start"]
        if "end" in payload and payload["end"]:
            kwargs["end"] = payload["end"]
        if not kwargs:
            return Error(
                message="no fields to update",
                user_message="Güncellenecek alan göndermedin.",
                user_notify=True,
                log_level="info",
            )
        if "start" in kwargs and "end" in kwargs and kwargs["start"] >= kwargs["end"]:
            return Error(
                message="start>=end",
                user_message="Bitiş zamanı başlangıçtan sonra olmalı.",
                user_notify=True,
                log_level="info",
            )
        event = adapter.update_event(event_id, **kwargs)
        return Success(
            data=_event_payload(event),
            ui_type="CalendarEvent",
            meta={"action": "update"},
        )

    def _delete(self, adapter: CalendarAdapter, payload: dict[str, Any]) -> Result:
        event_id = (payload.get("event_id") or "").strip()
        if not event_id:
            return Error(
                message="missing event_id",
                user_message="Hangi etkinlik siliniyor?",
                user_notify=True,
                log_level="info",
            )
        adapter.delete_event(event_id)
        return Success(
            data={"event_id": event_id},
            ui_type="text",
            meta={"action": "delete"},
        )


def _missing_fields(*, summary: str, start: str, end: str) -> list[str]:
    missing: list[str] = []
    if not summary:
        missing.append("başlık")
    if not start:
        missing.append("başlangıç")
    if not end:
        missing.append("bitiş")
    return missing


def _event_payload(event: CalendarEvent) -> dict[str, Any]:
    return asdict(event)
