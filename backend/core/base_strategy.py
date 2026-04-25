"""Abstract base class every capability strategy implements."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from .result import Result


class CapabilityStrategy(ABC):
    """Contract for a capability (mail, translation, calendar, document, …).

    Subclasses set ``name`` and ``intent_keys`` as class attributes so the
    registry / classifier can look them up. Implementations must not raise:
    convert exceptions into ``Error`` results inside ``execute``.
    """

    name: ClassVar[str] = ""
    intent_keys: ClassVar[tuple[str, ...]] = ()

    @abstractmethod
    def can_handle(self, intent: dict[str, Any]) -> bool:
        """Return True if this strategy should handle the given intent."""

    @abstractmethod
    async def execute(self, payload: dict[str, Any]) -> Result:
        """Execute the capability and return a ``Result``. Never raises."""

    def render_hint(self) -> str:
        """UI hint for the frontend (e.g. ``"MailCard"``). Override per capability."""
        return "text"
