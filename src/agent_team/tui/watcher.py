"""Session directory file watcher."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path

import watchfiles


class SessionWatcher:
    """Background watchfiles thread with debounced callback."""

    def __init__(
        self,
        session_dir: Path,
        callback: Callable[[], None],
        *,
        debounce_ms: int = 200,
    ) -> None:
        self._session_dir = session_dir
        self._callback = callback
        self._debounce_ms = debounce_ms
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return

        def run() -> None:
            last_call = 0.0
            for _changes in watchfiles.awatch(
                self._session_dir, recursive=True, stop_event=self._stop
            ):
                now = time.monotonic()
                if (now - last_call) * 1000 < self._debounce_ms:
                    continue
                last_call = now
                self._callback()

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
