"""Generic filesystem watcher built on watchfiles.

Background thread with rate-limit debounce and crash-safe callback. The
loop exits cleanly when stop() is called, regardless of where in the
debounce wait it is.
"""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

import watchfiles


class FileWatcher:
    def __init__(
        self,
        path: Path,
        callback: Callable[[], None],
        *,
        debounce_ms: int = 200,
        recursive: bool = False,
        label: str = "FileWatcher",
    ) -> None:
        self._path = path
        self._callback = callback
        self._debounce_ms = debounce_ms
        self._recursive = recursive
        self._label = label
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return

        def run() -> None:
            last_call = 0.0
            try:
                for _changes in watchfiles.watch(
                    self._path, recursive=self._recursive, stop_event=self._stop
                ):
                    elapsed_ms = (time.monotonic() - last_call) * 1000
                    if elapsed_ms < self._debounce_ms:
                        if self._stop.wait(
                            timeout=(self._debounce_ms - elapsed_ms) / 1000
                        ):
                            return
                    last_call = time.monotonic()
                    try:
                        self._callback()
                    except Exception as exc:
                        print(
                            f"{self._label} callback failed: {exc!r}",
                            file=sys.stderr,
                        )
            except Exception as exc:
                print(f"{self._label} loop crashed: {exc!r}", file=sys.stderr)

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
