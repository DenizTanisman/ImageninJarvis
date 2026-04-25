"""TTL-keyed SQLite cache for serialized payloads.

Used in 2.5+ to avoid re-classifying yesterday's mail batch every time
the user asks for the same daily summary. Values are JSON-serialized so
the schema is decoupled from any specific dataclass.

Schema (table: ``payload_cache``):
    cache_key   TEXT PRIMARY KEY
    payload     TEXT NOT NULL  -- JSON
    expires_at  TEXT NOT NULL  -- ISO-8601 UTC; row is ignored once now() > expires_at
    created_at  TEXT NOT NULL
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

DEFAULT_TTL_SECONDS = 24 * 60 * 60


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat()


class EmailCache:
    """JSON-payload cache with per-row expiry. Process-local (no locking).

    The class is misnamed slightly — it caches anything JSON-serializable —
    but the only caller in the MVP is the mail batching path, so we keep
    the name aligned with the CLAUDE.md spec.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS payload_cache (
                    cache_key   TEXT PRIMARY KEY,
                    payload     TEXT NOT NULL,
                    expires_at  TEXT NOT NULL,
                    created_at  TEXT NOT NULL
                )
                """
            )

    def put(
        self,
        key: str,
        value: Any,
        *,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        if not key:
            raise ValueError("cache key must not be empty")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        now = _utcnow()
        expires = now + timedelta(seconds=ttl_seconds)
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO payload_cache (cache_key, payload, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload     = excluded.payload,
                    expires_at  = excluded.expires_at,
                    created_at  = excluded.created_at
                """,
                (key, json.dumps(value), _iso(expires), _iso(now)),
            )

    def get(self, key: str) -> Any | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload, expires_at FROM payload_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        expires_at = datetime.fromisoformat(row[1])
        if expires_at <= _utcnow():
            return None
        return json.loads(row[0])

    def delete(self, key: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM payload_cache WHERE cache_key = ?", (key,))

    def clear_expired(self) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM payload_cache WHERE expires_at <= ?",
                (_iso(_utcnow()),),
            )
            return cur.rowcount

    def size(self) -> int:
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) FROM payload_cache").fetchone()
        return int(row[0]) if row else 0


def build_mail_key(*, user_id: str, kind: str, after: str, before: str) -> str:
    return f"mail:{user_id}:{kind}:{after}:{before}"
