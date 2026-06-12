"""Session directory file watcher.

Thin wrapper over agent_team._watcher.FileWatcher with the s7-specific
behavior baked in (recursive watch on session_dir, "SessionWatcher" label
for stderr diagnostics).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from agent_team._watcher import FileWatcher


class SessionWatcher(FileWatcher):
    def __init__(
        self,
        session_dir: Path,
        callback: Callable[[], None],
        *,
        debounce_ms: int = 200,
    ) -> None:
        super().__init__(
            session_dir,
            callback,
            debounce_ms=debounce_ms,
            recursive=True,
            label="SessionWatcher",
        )
