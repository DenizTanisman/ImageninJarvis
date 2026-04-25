from datetime import UTC, datetime

import pytest
from cryptography.fernet import Fernet

from services.token_store import StoredToken, TokenStore, TokenStoreError


@pytest.fixture()
def store(tmp_path):
    db = tmp_path / "tokens.db"
    return TokenStore(db, Fernet.generate_key().decode())


def test_constructor_rejects_empty_encryption_key(tmp_path) -> None:
    with pytest.raises(TokenStoreError):
        TokenStore(tmp_path / "x.db", "")


def test_constructor_rejects_invalid_key(tmp_path) -> None:
    with pytest.raises(TokenStoreError):
        TokenStore(tmp_path / "x.db", "not-a-fernet-key")


def test_save_then_load_round_trip(store: TokenStore) -> None:
    store.save(
        "default",
        refresh_token="refresh-123",
        access_token="access-456",
        expiry_iso=datetime(2026, 5, 1, tzinfo=UTC).isoformat(),
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
    loaded = store.load("default")
    assert isinstance(loaded, StoredToken)
    assert loaded.refresh_token == "refresh-123"
    assert loaded.access_token == "access-456"
    assert loaded.scopes == ("https://www.googleapis.com/auth/gmail.readonly",)


def test_save_overwrites_previous_row(store: TokenStore) -> None:
    store.save(
        "default",
        refresh_token="r1",
        access_token="a1",
        expiry_iso="2026-05-01T00:00:00+00:00",
        scopes=["scope.a"],
    )
    store.save(
        "default",
        refresh_token="r2",
        access_token="a2",
        expiry_iso="2026-06-01T00:00:00+00:00",
        scopes=["scope.b", "scope.a"],
    )
    loaded = store.load("default")
    assert loaded is not None
    assert loaded.refresh_token == "r2"
    assert loaded.access_token == "a2"
    assert loaded.scopes == ("scope.a", "scope.b")  # sorted + deduped


def test_load_returns_none_for_unknown_user(store: TokenStore) -> None:
    assert store.load("ghost") is None


def test_save_rejects_empty_refresh_token(store: TokenStore) -> None:
    with pytest.raises(TokenStoreError):
        store.save(
            "default",
            refresh_token="",
            access_token="a",
            expiry_iso="2026-05-01",
            scopes=["scope"],
        )


def test_delete_removes_row(store: TokenStore) -> None:
    store.save(
        "default",
        refresh_token="r",
        access_token="a",
        expiry_iso="2026-05-01T00:00:00+00:00",
        scopes=["scope"],
    )
    store.delete("default")
    assert store.load("default") is None


def test_load_with_rotated_key_raises(tmp_path) -> None:
    key1 = Fernet.generate_key().decode()
    store1 = TokenStore(tmp_path / "t.db", key1)
    store1.save(
        "default",
        refresh_token="r",
        access_token="a",
        expiry_iso="2026-05-01T00:00:00+00:00",
        scopes=["scope"],
    )
    key2 = Fernet.generate_key().decode()
    store2 = TokenStore(tmp_path / "t.db", key2)
    with pytest.raises(TokenStoreError):
        store2.load("default")


def test_ciphertext_is_not_plaintext(tmp_path) -> None:
    """Stored bytes should not contain the cleartext refresh token."""
    import sqlite3

    store = TokenStore(tmp_path / "t.db", Fernet.generate_key().decode())
    store.save(
        "default",
        refresh_token="super-secret-refresh",
        access_token="super-secret-access",
        expiry_iso="2026-05-01T00:00:00+00:00",
        scopes=["scope"],
    )
    raw = sqlite3.connect(tmp_path / "t.db").execute(
        "SELECT refresh_token, access_token FROM oauth_tokens WHERE user_id = ?",
        ("default",),
    ).fetchone()
    assert b"super-secret-refresh" not in raw[0]
    assert b"super-secret-access" not in raw[1]
