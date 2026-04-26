from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CalendarEvent:
    """Plain-data view of a Google Calendar event.

    ``start`` / ``end`` are RFC3339 strings (e.g. ``2026-04-28T14:00:00+03:00``)
    so the frontend can treat them as opaque ISO timestamps without
    pulling in pytz / zoneinfo.
    """

    id: str
    summary: str
    start: str
    end: str
    description: str = ""
    html_link: str = ""
