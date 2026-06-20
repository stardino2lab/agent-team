"""TmuxBackend argv (S13b) — only the two forks vs psmux; everything else inherited."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_team.terminal_backend import TerminalBackend
from agent_team.tmux_backend import TmuxBackend


@pytest.fixture
def tmux() -> TmuxBackend:
    return TmuxBackend(mock=True)


def test_name_is_tmux(tmux: TmuxBackend) -> None:
    assert tmux.name == "tmux"


def test_satisfies_protocol(tmux: TmuxBackend) -> None:
    assert isinstance(tmux, TerminalBackend)


def test_new_session_command_is_trailing_no_separator(tmux: TmuxBackend) -> None:
    tmux.new_session("sess", command="claude", cwd=Path("/tmp/test"))
    args = tmux.recorded_calls[0].args
    assert args[:4] == ["new-session", "-d", "-s", "sess"]
    assert "--" not in args  # the fork: tmux has no `--` separator
    assert args[-1] == "claude"  # command is the trailing arg


def test_split_pane_uses_lines_percent_and_trailing_command(tmux: TmuxBackend) -> None:
    tmux.new_session("sess")
    tmux.split_pane(
        "sess", direction="vertical", size_percent=30, command="codex"
    )
    args = tmux.recorded_calls[1].args
    assert "split-window" in args and "-v" in args
    # the fork: tmux>=3.4 uses `-l N%`, not psmux's `-p N`
    assert "-l" in args and "30%" in args
    assert "-p" not in args
    assert "--" not in args
    assert args[-1] == "codex"


def test_send_keys_identical_to_psmux(tmux: TmuxBackend) -> None:
    # send-keys is byte-identical (psmux is a tmux fork): -l literal then bare submit.
    tmux.new_session("sess")
    tmux.send_keys("%0", "go", submit_keys=("Enter",))
    assert tmux.recorded_calls[1].args == ["send-keys", "-t", "%0", "-l", "go"]
    assert tmux.recorded_calls[2].args == ["send-keys", "-t", "%0", "Enter"]


def test_capture_and_pipe_identical(tmux: TmuxBackend, tmp_path: Path) -> None:
    tmux.capture_pane("%0")
    cap = next(c for c in tmux.recorded_calls if "capture-pane" in c.args)
    assert cap.args == ["capture-pane", "-t", "%0", "-p"]
    tmux.pipe_pane("%0", tmp_path / "t.log")
    pipe = next(c for c in tmux.recorded_calls if "pipe-pane" in c.args)
    assert pipe.args[:4] == ["pipe-pane", "-t", "%0", "-o"]


def test_pane_minting_inherited(tmux: TmuxBackend) -> None:
    p0 = tmux.new_session("sess")
    p1 = tmux.split_pane("sess")
    assert (p0, p1) == ("%0", "%1")
