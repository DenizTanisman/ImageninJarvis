import os
import time
from pathlib import Path

from capabilities.document.ingest import (
    cleanup_sandbox,
    sweep_old_sandboxes,
)


def test_cleanup_sandbox_removes_dir(tmp_path: Path) -> None:
    target = tmp_path / "abc"
    target.mkdir()
    (target / "file.txt").write_text("x")
    cleanup_sandbox(target)
    assert not target.exists()


def test_cleanup_sandbox_idempotent_on_missing_dir(tmp_path: Path) -> None:
    cleanup_sandbox(tmp_path / "never-existed")  # must not raise


def test_sweep_removes_directories_older_than_cutoff(tmp_path: Path) -> None:
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    (fresh / "x").write_text("x")

    stale = tmp_path / "stale"
    stale.mkdir()
    (stale / "x").write_text("x")
    # Backdate stale to two days ago.
    two_days = time.time() - (2 * 24 * 60 * 60)
    os.utime(stale, (two_days, two_days))

    removed = sweep_old_sandboxes(tmp_path)
    assert removed == 1
    assert fresh.exists()
    assert not stale.exists()


def test_sweep_returns_zero_when_root_missing(tmp_path: Path) -> None:
    removed = sweep_old_sandboxes(tmp_path / "no-such-root")
    assert removed == 0


def test_sweep_ignores_files_at_root(tmp_path: Path) -> None:
    (tmp_path / "stray.txt").write_text("hi")
    removed = sweep_old_sandboxes(tmp_path)
    assert removed == 0
    assert (tmp_path / "stray.txt").exists()


def test_sweep_uses_custom_max_age(tmp_path: Path) -> None:
    """Pass max_age_seconds=0 so every dir is "stale" — useful when the
    operator wants to flush the sandbox immediately."""
    d = tmp_path / "anything"
    d.mkdir()
    removed = sweep_old_sandboxes(tmp_path, max_age_seconds=0)
    assert removed == 1
    assert not d.exists()
