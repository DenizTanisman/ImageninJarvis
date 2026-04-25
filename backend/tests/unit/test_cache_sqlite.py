from datetime import UTC, datetime, timedelta

import pytest

from services.cache_sqlite import EmailCache, build_mail_key


@pytest.fixture()
def cache(tmp_path):
    return EmailCache(tmp_path / "cache.db")


def test_get_returns_none_for_missing_key(cache: EmailCache) -> None:
    assert cache.get("ghost") is None


def test_put_then_get_round_trip(cache: EmailCache) -> None:
    cache.put("k", {"answer": 42, "list": [1, 2, 3]})
    assert cache.get("k") == {"answer": 42, "list": [1, 2, 3]}


def test_put_overwrites_existing(cache: EmailCache) -> None:
    cache.put("k", "first")
    cache.put("k", "second")
    assert cache.get("k") == "second"
    assert cache.size() == 1


def test_get_returns_none_after_expiry(cache: EmailCache, monkeypatch) -> None:
    cache.put("k", "still-here", ttl_seconds=1)
    fake_now = datetime.now(UTC) + timedelta(seconds=10)
    monkeypatch.setattr("services.cache_sqlite._utcnow", lambda: fake_now)
    assert cache.get("k") is None


def test_clear_expired_deletes_only_old_rows(cache: EmailCache, monkeypatch) -> None:
    cache.put("fresh", "ok", ttl_seconds=3600)
    cache.put("stale", "old", ttl_seconds=1)
    fake_now = datetime.now(UTC) + timedelta(seconds=10)
    monkeypatch.setattr("services.cache_sqlite._utcnow", lambda: fake_now)
    removed = cache.clear_expired()
    assert removed == 1
    assert cache.size() == 1
    assert cache.get("fresh") == "ok"


def test_put_rejects_empty_key(cache: EmailCache) -> None:
    with pytest.raises(ValueError):
        cache.put("", "value")


def test_put_rejects_non_positive_ttl(cache: EmailCache) -> None:
    with pytest.raises(ValueError):
        cache.put("k", "v", ttl_seconds=0)


def test_delete_removes_row(cache: EmailCache) -> None:
    cache.put("k", "v")
    cache.delete("k")
    assert cache.get("k") is None


def test_build_mail_key_is_deterministic() -> None:
    a = build_mail_key(user_id="default", kind="daily", after="2026-04-24", before="2026-04-25")
    b = build_mail_key(user_id="default", kind="daily", after="2026-04-24", before="2026-04-25")
    assert a == b
    assert a == "mail:default:daily:2026-04-24:2026-04-25"
