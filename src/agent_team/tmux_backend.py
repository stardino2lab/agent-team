"""tmux pane backend (the POSIX TerminalBackend) for Linux/macOS.

tmux and psmux share ~all subcommand syntax; psmux is itself a tmux fork. The only
forks are: (1) `new-session`/`split-window` take the command as a TRAILING arg, not
after a `--` separator; (2) tmux >= 3.4 removed `split-window -p N` in favour of
`-l N%`. So TmuxBackend reuses PsmuxBackend's whole subprocess implementation and
overrides only those two argv shapes + name/executable.

Targets tmux >= 3.4 (the `-l N%` split form). Min version is documented in
tests/manual/s13-tmux-linux.md; older tmux only affects cosmetic pane sizing.
"""

from __future__ import annotations

from agent_team.psmux_backend import PsmuxBackend


class TmuxBackend(PsmuxBackend):
    def __init__(self, *, executable: str = "tmux", mock: bool = False) -> None:
        super().__init__(executable=executable, mock=mock)

    @property
    def name(self) -> str:
        return "tmux"

    def _build_argv(self, *parts: str, command: str | None = None) -> list[str]:
        # tmux takes the command as a trailing arg (no `--` separator).
        argv = list(parts)
        if command is not None:
            argv.append(command)
        return argv

    def _size_args(self, size_percent: int) -> list[str]:
        # tmux >= 3.4: percentage split is `-l N%` (3.4 removed `-p`).
        return ["-l", f"{size_percent}%"]
