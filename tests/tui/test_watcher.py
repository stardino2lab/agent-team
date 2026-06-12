"""Real watchfiles integration for SessionWatcher (no MagicMock)."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from agent_team.tui.watcher import SessionWatcher


def _wait(event: threading.Event, timeout: float = 8.0) -> bool:
    return event.wait(timeout=timeout)


@pytest.fixture
def watch_dir(tmp_path: Path) -> Path:
    d = tmp_path / "session"
    d.mkdir()
    return d


def test_watcher_fires_callback_on_file_change(watch_dir: Path) -> None:
    fired = threading.Event()

    def callback() -> None:
        fired.set()

    watcher = SessionWatcher(watch_dir, callback, debounce_ms=50)
    watcher.start()
    try:
        import time as _t

        _t.sleep(0.3)  # let watchfiles attach to the directory
        (watch_dir / "mail.jsonl").write_text("hello\n", encoding="utf-8")
        assert _wait(fired), "callback was not invoked within 8s"
    finally:
        watcher.stop()


def test_watcher_survives_callback_exception(watch_dir: Path, capsys) -> None:
    calls = []
    second_call = threading.Event()

    def callback() -> None:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("boom")
        second_call.set()

    watcher = SessionWatcher(watch_dir, callback, debounce_ms=50)
    watcher.start()
    try:
        (watch_dir / "first.txt").write_text("a", encoding="utf-8")
        # wait long enough for the first (failing) callback to fire and debounce to clear
        import time as _t

        _t.sleep(0.4)
        (watch_dir / "second.txt").write_text("b", encoding="utf-8")
        assert _wait(second_call), "watcher thread died after first callback raised"
    finally:
        watcher.stop()

    err = capsys.readouterr().err
    assert "SessionWatcher callback failed" in err
