"""Encrypted SQLite token store.

Stores Google OAuth tokens (refresh + short-lived access) under a single
``user_id`` row. All sensitive columns are Fernet-encrypted with the
``ENCRYPTION_KEY`` from settings, so a leaked DB file alone is useless.

Schema (table: ``oauth_tokens``):
    user_id        TEXT  PRIMARY KEY  -- 'default' until multi-user
    refresh_token  BLOB  NOT NULL     -- Fernet ciphertext
    access_token   BLOB  NOT NULL     -- Fernet ciphertext
    expiry_iso     TEXT  NOT NULL     -- token expiry, ISO-8601 UTC
    scopes         TEXT  NOT NULL     -- comma-separated
    updated_at     TEXT  NOT NULL     -- ISO-8601 UTC

The store also records which OAuth scopes were granted so we can detect
whether a re-consent is needed when a new capability adds a scope (e.g.
gmail.send in 2.7).
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class StoredToken:
    user_id: str
    refresh_token: str
    access_token: str
    expiry_iso: str
    scopes: tuple[str, ...]


class TokenStoreError(RuntimeError):
    pass


class TokenStore:
    def __init__(self, db_path: str | Path, encryption_key: str) -> None:
        if not encryption_key:
            raise TokenStoreError("ENCRYPTION_KEY is required for the token store")
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._fernet = Fernet(encryption_key.encode("utf-8"))
        except (ValueError, TypeError) as exc:
            raise TokenStoreError(
                "ENCRYPTION_KEY is not a valid Fernet key (32-byte urlsafe base64)"
            ) from exc
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._db_path)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_tokens (
                    user_id        TEXT PRIMARY KEY,
                    refresh_token  BLOB NOT NULL,
                    access_token   BLOB NOT NULL,
                    expiry_iso     TEXT NOT NULL,
                    scopes         TEXT NOT NULL,
                    updated_at     TEXT NOT NULL
                )
                """
            )

    def save(
        self,
        user_id: str,
        *,
        refresh_token: str,
        access_token: str,
        expiry_iso: str,
        scopes: Iterable[str],
    ) -> None:
        if not refresh_token:
            raise TokenStoreError("refresh_token must not be empty")
        scope_string = ",".join(sorted({s.strip() for s in scopes if s.strip()}))
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO oauth_tokens (
                    user_id, refresh_token, access_token, expiry_iso, scopes, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    refresh_token = excluded.refresh_token,
                    access_token  = excluded.access_token,
                    expiry_iso    = excluded.expiry_iso,
                    scopes        = excluded.scopes,
                    updated_at    = excluded.updated_at
                """,
                (
                    user_id,
                    self._fernet.encrypt(refresh_token.encode("utf-8")),
                    self._fernet.encrypt(access_token.encode("utf-8")),
                    expiry_iso,
                    scope_string,
                    _utcnow_iso(),
                ),
            )

    def load(self, user_id: str) -> StoredToken | None:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT refresh_token, access_token, expiry_iso, scopes
                FROM oauth_tokens WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        try:
            refresh = self._fernet.decrypt(row[0]).decode("utf-8")
            access = self._fernet.decrypt(row[1]).decode("utf-8")
        except InvalidToken as exc:
            raise TokenStoreError(
                "Stored token could not be decrypted; ENCRYPTION_KEY may have changed"
            ) from exc
        scopes = tuple(s for s in row[3].split(",") if s)
        return StoredToken(
            user_id=user_id,
            refresh_token=refresh,
            access_token=access,
            expiry_iso=row[2],
            scopes=scopes,
        )

    def delete(self, user_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM oauth_tokens WHERE user_id = ?", (user_id,))
