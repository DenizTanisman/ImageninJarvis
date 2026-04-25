"""Result type for capability execution.

Strategies return ``Result`` (a ``Success | Error`` union) instead of raising,
so the dispatcher can handle every outcome without try/except gymnastics and
the client gets a uniform response shape.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

LogLevel = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class Success:
    data: Any
    ui_type: str = "text"
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def is_ok(self) -> bool:
        return True

    @property
    def is_err(self) -> bool:
        return False


@dataclass(frozen=True)
class Error:
    message: str
    user_message: str
    user_notify: bool = True
    log_level: LogLevel = "error"
    retry_after: int | None = None

    @property
    def is_ok(self) -> bool:
        return False

    @property
    def is_err(self) -> bool:
        return True


Result = Success | Error


def is_success(result: Result) -> bool:
    return isinstance(result, Success)


def is_error(result: Result) -> bool:
    return isinstance(result, Error)
