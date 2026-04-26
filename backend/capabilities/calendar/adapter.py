"""Google Calendar v3 wrapper.

Mirrors GmailAdapter: pre-built ``Credentials`` go in, plain dataclasses
come out. All four CRUD operations (list / create / update / delete)
funnel through ``num_retries=3`` so transient TLS resets don't surface
as 500s, and any ``HttpError`` / ``OSError`` is wrapped as
``CalendarAdapterError`` so the strategy layer can return a friendly
``Error(...)`` instead of leaking transport exceptions.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import CalendarEvent

logger = logging.getLogger(__name__)

EXECUTE_NUM_RETRIES = 3
DEFAULT_DAYS_AHEAD = 7
DEFAULT_CALENDAR_ID = "primary"


class CalendarAdapterError(RuntimeError):
    pass


class CalendarAdapter:
    """Thin synchronous wrapper around Calendar v3."""

    def __init__(self, credentials: Credentials, *, service: Any | None = None) -> None:
        if service is not None:
            self._service = service
        else:
            self._service = build(
                "calendar", "v3", credentials=credentials, cache_discovery=False
            )

    def list_events(
        self,
        *,
        days: int = DEFAULT_DAYS_AHEAD,
        calendar_id: str = DEFAULT_CALENDAR_ID,
        max_results: int = 50,
    ) -> list[CalendarEvent]:
        """Return events between *now* and *now + days* on the chosen calendar.

        ``singleEvents=True`` expands recurring events; ``orderBy=startTime``
        keeps the result deterministic so the frontend can render straight
        from the list.
        """
        if days <= 0:
            return []
        now = datetime.now(UTC)
        time_min = _rfc3339(now)
        time_max = _rfc3339(now + timedelta(days=days))
        try:
            response = (
                self._service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=max_results,
                )
                .execute(num_retries=EXECUTE_NUM_RETRIES)
            )
        except (HttpError, OSError) as exc:
            raise CalendarAdapterError(f"Calendar list failed: {exc}") from exc

        events = []
        for raw in response.get("items", []):
            event = _parse_event(raw)
            if event is not None:
                events.append(event)
        return events

    def create_event(
        self,
        *,
        summary: str,
        start: str,
        end: str,
        description: str = "",
        calendar_id: str = DEFAULT_CALENDAR_ID,
    ) -> CalendarEvent:
        body = _build_event_body(
            summary=summary, start=start, end=end, description=description
        )
        try:
            raw = (
                self._service.events()
                .insert(calendarId=calendar_id, body=body)
                .execute(num_retries=EXECUTE_NUM_RETRIES)
            )
        except (HttpError, OSError) as exc:
            raise CalendarAdapterError(f"Calendar create failed: {exc}") from exc
        parsed = _parse_event(raw)
        if parsed is None:
            raise CalendarAdapterError("Calendar create returned no id")
        return parsed

    def update_event(
        self,
        event_id: str,
        *,
        summary: str | None = None,
        start: str | None = None,
        end: str | None = None,
        description: str | None = None,
        calendar_id: str = DEFAULT_CALENDAR_ID,
    ) -> CalendarEvent:
        """Patch only the fields the caller actually set.

        Using ``events.patch`` (not ``update``) lets the caller leave any
        argument as ``None`` to mean "don't touch" — the frontend form may
        only edit one or two fields without re-submitting the rest.
        """
        if not event_id:
            raise CalendarAdapterError("update_event requires an event id")
        body: dict[str, Any] = {}
        if summary is not None:
            body["summary"] = summary
        if description is not None:
            body["description"] = description
        if start is not None:
            body["start"] = {"dateTime": start}
        if end is not None:
            body["end"] = {"dateTime": end}
        if not body:
            raise CalendarAdapterError("update_event requires at least one field")
        try:
            raw = (
                self._service.events()
                .patch(calendarId=calendar_id, eventId=event_id, body=body)
                .execute(num_retries=EXECUTE_NUM_RETRIES)
            )
        except (HttpError, OSError) as exc:
            raise CalendarAdapterError(f"Calendar update failed: {exc}") from exc
        parsed = _parse_event(raw)
        if parsed is None:
            raise CalendarAdapterError("Calendar update returned no id")
        return parsed

    def delete_event(
        self, event_id: str, *, calendar_id: str = DEFAULT_CALENDAR_ID
    ) -> None:
        if not event_id:
            raise CalendarAdapterError("delete_event requires an event id")
        try:
            (
                self._service.events()
                .delete(calendarId=calendar_id, eventId=event_id)
                .execute(num_retries=EXECUTE_NUM_RETRIES)
            )
        except (HttpError, OSError) as exc:
            raise CalendarAdapterError(f"Calendar delete failed: {exc}") from exc


def _build_event_body(
    *, summary: str, start: str, end: str, description: str
) -> dict[str, Any]:
    if not summary.strip():
        raise CalendarAdapterError("Event summary cannot be empty")
    if not start or not end:
        raise CalendarAdapterError("Event start and end are required")
    body: dict[str, Any] = {
        "summary": summary,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
    }
    if description:
        body["description"] = description
    return body


def _parse_event(raw: dict[str, Any]) -> CalendarEvent | None:
    event_id = raw.get("id")
    if not isinstance(event_id, str) or not event_id:
        return None
    start = raw.get("start") or {}
    end = raw.get("end") or {}
    return CalendarEvent(
        id=event_id,
        summary=raw.get("summary") or "(no title)",
        start=start.get("dateTime") or start.get("date") or "",
        end=end.get("dateTime") or end.get("date") or "",
        description=raw.get("description") or "",
        html_link=raw.get("htmlLink") or "",
    )


def _rfc3339(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()
