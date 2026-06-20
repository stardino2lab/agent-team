"""Terminal-multiplexer backend abstraction (psmux on Windows, tmux on POSIX).

Leaf module — imports only stdlib. Owns the shared value types, the neutral
exception hierarchy, the `TerminalBackend` Protocol that `PsmuxBackend` (and, from
S13b, `TmuxBackend`) satisfy, a shell-aware quoting helper, and the backend
factory. The factory lazily imports the concrete backends to avoid a cycle
(`psmux_backend` imports THIS module, never the reverse at module scope).
"""

from __future__ import annotations

import os
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable


class TerminalBackendError(RuntimeError):
    """Base for terminal-backend failures."""


class BackendNotFoundError(FileNotFoundError):
    """Raised when the backend executable is not in PATH.

    Subclasses FileNotFoundError so existing `except FileNotFoundError` callers
    keep working; `PsmuxNotFoundError` aliases this for back-compat.
    """


class BackendCommandError(TerminalBackendError):
    """Raised when a backend command exits non-zero. `PsmuxCommandError` aliases it."""

    def __init__(
        self,
        message: str,
        *,
        exit_code: int,
        command_args: list[str],
        stderr: str,
    ) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.command_args = command_args
        self.stderr = stderr

    @property
    def args(self) -> list[str]:
        """Alias for sketch compatibility."""
        return self.command_args


@dataclass
class PaneInfo:
    pane_id: str


@dataclass
class RecordedCall:
    args: list[str]
    cwd: str | None = None


@runtime_checkable
class TerminalBackend(Protocol):
    """The pane-control surface the orchestrator/runner depend on.

    Both `PsmuxBackend` and the future `TmuxBackend` satisfy this. Signatures
    mirror the concrete backends exactly (note `send_keys` takes `submit_keys`,
    not `enter`).
    """

    @property
    def name(self) -> str: ...

    @property
    def recorded_calls(self) -> list[RecordedCall]: ...

    def new_session(
        self, name: str, *, command: str | None = None, cwd: Path | None = None
    ) -> str: ...

    def split_pane(
        self,
        session: str,
        *,
        direction: Literal["horizontal", "vertical"] = "horizontal",
        command: str | None = None,
        cwd: Path | None = None,
        size_percent: int | None = None,
    ) -> str: ...

    def send_keys(
        self, target: str, keys: str, *, submit_keys: tuple[str, ...] = ("Enter",)
    ) -> None: ...

    def kill_pane(self, target: str) -> None: ...

    def kill_session(self, name: str) -> None: ...

    def list_panes(self, session: str) -> list[PaneInfo]: ...

    def capture_pane(self, target: str) -> str: ...

    def pipe_pane(self, target: str, log_path: Path) -> None: ...


def quote_pane_arg(value: str, *, shell_family: Literal["windows", "posix"]) -> str:
    """Quote a single value for the pane shell — QUOTING ONLY, never path-form.

    windows (cmd.exe/PowerShell): double-quote wrap, matching today's launch lines
    and pipe-pane redirect exactly. posix (bash/zsh/sh): shlex.quote. Callers that
    need forward slashes apply `.as_posix()` to the path BEFORE quoting; this helper
    must not change separators (doing so would flip Windows launch paths and break
    byte-identical behavior).
    """
    if shell_family == "posix":
        return shlex.quote(value)
    if shell_family == "windows":
        return f'"{value}"'
    raise ValueError(f"unknown shell_family: {shell_family!r}")


def make_terminal_backend(*, mock: bool = False) -> TerminalBackend:
    """Select and construct the pane backend.

    Order: `mock=True` short-circuits BEFORE any executable lookup (the unit/CI
    path — must work on a box with no psmux/tmux). Else `AGENT_TEAM_BACKEND`
    (`psmux`|`tmux`) if set, else platform default (win32→psmux, otherwise tmux).
    An unknown env value is an explicit error, never a silent fallthrough.
    """
    if mock:
        from agent_team.psmux_backend import PsmuxBackend

        return PsmuxBackend(mock=True)

    name = os.environ.get("AGENT_TEAM_BACKEND")
    if name is None:
        name = "psmux" if sys.platform == "win32" else "tmux"

    if name == "psmux":
        from agent_team.psmux_backend import PsmuxBackend

        return PsmuxBackend()
    if name == "tmux":
        from agent_team.tmux_backend import TmuxBackend

        return TmuxBackend()
    raise ValueError(
        f"Unknown AGENT_TEAM_BACKEND: {name!r} (expected 'psmux' or 'tmux')"
    )
