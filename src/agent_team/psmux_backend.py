"""psmux subprocess wrapper for pane control."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agent_team._io import InvalidPathSegmentError, safe_segment

_PANE_TARGET = re.compile(r"%[0-9]+")
_STDERR_MAX = 500


class PsmuxNotFoundError(FileNotFoundError):
    """Raised when psmux executable is not in PATH."""


class PsmuxCommandError(RuntimeError):
    """Raised when a psmux command exits non-zero."""

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


class PsmuxBackend:
    def __init__(self, *, executable: str = "psmux", mock: bool = False) -> None:
        self._executable_name = executable
        self._mock = mock
        self._recorded: list[RecordedCall] = []
        self._mock_panes: dict[str, set[str]] = {}
        self._mock_next_id = 0
        self._executable: str | None = None
        if not mock:
            resolved = shutil.which(executable)
            if resolved is None:
                raise PsmuxNotFoundError(f"psmux executable not found: {executable}")
            self._executable = resolved

    @property
    def recorded_calls(self) -> list[RecordedCall]:
        if not self._mock:
            return []
        return [RecordedCall(args=list(c.args), cwd=c.cwd) for c in self._recorded]

    def new_session(
        self,
        name: str,
        *,
        command: str | None = None,
        cwd: Path | None = None,
    ) -> str:
        safe_name = self._validate_session_name(name)
        parts = ["new-session", "-d", "-s", safe_name]
        if cwd is not None:
            parts.extend(["-c", str(cwd.resolve())])
        args = self._build_argv(*parts, command=command)
        self._run(args, cwd=cwd)

        if self._mock:
            pane_id = self._next_mock_pane_id()
            self._mock_panes.setdefault(safe_name, set()).add(pane_id)
            return pane_id

        panes = self.list_panes(safe_name)
        if not panes:
            raise PsmuxCommandError(
                f"new-session produced no panes for {safe_name!r}",
                exit_code=0,
                command_args=args,
                stderr="",
            )
        return panes[0].pane_id

    def split_pane(
        self,
        session: str,
        *,
        direction: Literal["horizontal", "vertical"] = "horizontal",
        command: str | None = None,
        cwd: Path | None = None,
        size_percent: int | None = None,
    ) -> str:
        safe_session = self._validate_session_name(session)
        if size_percent is not None and not 1 <= size_percent <= 100:
            raise ValueError(f"size_percent must be 1..100, got {size_percent}")

        flag = "-h" if direction == "horizontal" else "-v"
        parts = ["split-window", "-t", safe_session, "-d", flag]
        if size_percent is not None:
            parts.extend(["-p", str(size_percent)])
        if cwd is not None:
            parts.extend(["-c", str(cwd.resolve())])
        args = self._build_argv(*parts, command=command)

        before: set[str] = set()
        if not self._mock:
            before = {p.pane_id for p in self.list_panes(safe_session)}

        self._run(args, cwd=cwd)

        if self._mock:
            pane_id = self._next_mock_pane_id()
            self._mock_panes.setdefault(safe_session, set()).add(pane_id)
            return pane_id

        after = {p.pane_id for p in self.list_panes(safe_session)}
        new_ids = after - before
        if len(new_ids) != 1:
            raise PsmuxCommandError(
                f"split-window did not produce exactly one new pane for {safe_session!r}",
                exit_code=0,
                command_args=args,
                stderr="",
            )
        return new_ids.pop()

    def send_keys(self, target: str, keys: str, *, enter: bool = True) -> None:
        safe_target = self._validate_target(target)
        parts = ["send-keys", "-t", safe_target, "-l", keys]
        if enter:
            parts.append("Enter")
        self._run(parts)

    def kill_pane(self, target: str) -> None:
        safe_target = self._validate_target(target)
        self._run(["kill-pane", "-t", safe_target])
        if self._mock and safe_target.startswith("%"):
            for panes in self._mock_panes.values():
                panes.discard(safe_target)

    def kill_session(self, name: str) -> None:
        """Kill an entire psmux session. No-op if the session does not exist."""
        safe_name = self._validate_session_name(name)
        try:
            self._run(["kill-session", "-t", safe_name])
        except PsmuxCommandError:
            # No such session - treat as already-cleaned.
            pass
        if self._mock:
            self._mock_panes.pop(safe_name, None)

    def list_panes(self, session: str) -> list[PaneInfo]:
        safe_session = self._validate_session_name(session)
        if self._mock:
            ids = sorted(self._mock_panes.get(safe_session, set()))
            return [PaneInfo(pane_id=p) for p in ids]

        output = self._run(
            ["list-panes", "-t", safe_session, "-F", "#{pane_id}"],
        )
        pane_ids = self._parse_pane_ids(output)
        return [PaneInfo(pane_id=p) for p in pane_ids]

    def _validate_session_name(self, name: str) -> str:
        return safe_segment(name, "psmux_session")

    def _validate_target(self, target: str) -> str:
        if target.startswith("%"):
            if not _PANE_TARGET.fullmatch(target):
                raise InvalidPathSegmentError(f"Invalid pane target: {target!r}")
            return target
        return safe_segment(target, "psmux_session")

    def _build_argv(self, *parts: str, command: str | None = None) -> list[str]:
        argv = list(parts)
        if command is not None:
            argv.extend(["--", command])
        return argv

    def _next_mock_pane_id(self) -> str:
        pane_id = f"%{self._mock_next_id}"
        self._mock_next_id += 1
        return pane_id

    def _parse_pane_ids(self, output: str) -> list[str]:
        pane_ids: list[str] = []
        for line in output.splitlines():
            pane_id = line.strip()
            if not pane_id:
                continue
            if not _PANE_TARGET.fullmatch(pane_id):
                raise PsmuxCommandError(
                    f"invalid pane_id from list-panes: {pane_id!r}",
                    exit_code=0,
                    command_args=["list-panes"],
                    stderr="",
                )
            pane_ids.append(pane_id)
        return pane_ids

    def _run(self, args: list[str], *, cwd: Path | None = None) -> str:
        cwd_str = str(cwd.resolve()) if cwd is not None else None
        if self._mock:
            self._recorded.append(RecordedCall(args=list(args), cwd=cwd_str))
            return ""

        assert self._executable is not None
        full_argv = [self._executable, *args]
        result = subprocess.run(
            full_argv,
            shell=False,
            capture_output=True,
            text=True,
            cwd=cwd_str,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "")[:_STDERR_MAX]
            raise PsmuxCommandError(
                f"psmux failed ({result.returncode}): {stderr}",
                exit_code=result.returncode,
                command_args=args,
                stderr=stderr,
            )
        return result.stdout
