"""PsmuxBackend unit tests."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent_team._io import InvalidPathSegmentError
from agent_team.psmux_backend import PsmuxBackend, PsmuxCommandError, PsmuxNotFoundError


def test_mock_new_session_records_argv_and_returns_pane(psmux_backend: PsmuxBackend) -> None:
    project = Path("c:/DEV/test")
    pane_id = psmux_backend.new_session(
        "agent-team-demo",
        command="claude",
        cwd=project,
    )
    assert pane_id == "%0"
    call = psmux_backend.recorded_calls[0]
    assert call.args[:4] == ["new-session", "-d", "-s", "agent-team-demo"]
    assert "-c" in call.args
    assert call.args[-2:] == ["--", "claude"]
    assert call.cwd == str(project.resolve())


def test_mock_split_pane_horizontal_and_vertical(psmux_backend: PsmuxBackend) -> None:
    psmux_backend.new_session("sess")
    p1 = psmux_backend.split_pane("sess", direction="horizontal")
    p2 = psmux_backend.split_pane(
        "sess",
        direction="vertical",
        size_percent=30,
        command="codex",
        cwd=Path("c:/DEV/proj"),
    )
    assert p1 == "%1"
    assert p2 == "%2"
    horizontal = psmux_backend.recorded_calls[1].args
    assert "split-window" in horizontal
    assert "-d" in horizontal
    assert "-h" in horizontal
    vertical = psmux_backend.recorded_calls[2].args
    assert "-v" in vertical
    assert "-p" in vertical
    assert vertical[-2:] == ["--", "codex"]
    assert psmux_backend.recorded_calls[2].cwd == str(Path("c:/DEV/proj").resolve())


def test_mock_send_keys_with_and_without_enter(psmux_backend: PsmuxBackend) -> None:
    psmux_backend.new_session("sess")
    psmux_backend.send_keys("%0", "hello")
    psmux_backend.send_keys("%0", "-flag", enter=False)
    assert psmux_backend.recorded_calls[1].args == [
        "send-keys",
        "-t",
        "%0",
        "-l",
        "hello",
        "Enter",
    ]
    assert psmux_backend.recorded_calls[2].args == [
        "send-keys",
        "-t",
        "%0",
        "-l",
        "-flag",
    ]


def test_mock_kill_pane_removes_from_list(psmux_backend: PsmuxBackend) -> None:
    psmux_backend.new_session("sess")
    psmux_backend.split_pane("sess")
    assert len(psmux_backend.list_panes("sess")) == 2
    psmux_backend.kill_pane("%1")
    assert psmux_backend.recorded_calls[-1].args == ["kill-pane", "-t", "%1"]
    assert [p.pane_id for p in psmux_backend.list_panes("sess")] == ["%0"]


def test_mock_list_panes_tracks_state(psmux_backend: PsmuxBackend) -> None:
    psmux_backend.new_session("sess")
    psmux_backend.split_pane("sess")
    panes = psmux_backend.list_panes("sess")
    assert [p.pane_id for p in panes] == ["%0", "%1"]


def test_recorded_calls_returns_defensive_copy(psmux_backend: PsmuxBackend) -> None:
    psmux_backend.new_session("sess")
    calls = psmux_backend.recorded_calls
    calls[0].args.append("mutated")
    assert "mutated" not in psmux_backend.recorded_calls[0].args


def test_missing_executable_raises() -> None:
    with patch("agent_team.psmux_backend.shutil.which", return_value=None):
        with pytest.raises(PsmuxNotFoundError):
            PsmuxBackend(mock=False)


def test_safe_segment_rejects_bad_session_name(psmux_backend: PsmuxBackend) -> None:
    with pytest.raises(InvalidPathSegmentError):
        psmux_backend.new_session("../evil")


def test_invalid_pane_target_rejected(psmux_backend: PsmuxBackend) -> None:
    with pytest.raises(InvalidPathSegmentError):
        psmux_backend.kill_pane("%bad")


def test_psmux_command_error_on_nonzero_exit() -> None:
    with patch("agent_team.psmux_backend.shutil.which", return_value="C:\\psmux.exe"):
        backend = PsmuxBackend(mock=False)
        failed = MagicMock(returncode=1, stdout="", stderr="boom")
        with patch("agent_team.psmux_backend.subprocess.run", return_value=failed):
            with pytest.raises(PsmuxCommandError) as exc_info:
                backend.new_session("sess")
        err = exc_info.value
        assert err.exit_code == 1
        assert err.stderr == "boom"
        assert err.command_args[0] == "new-session"
        assert err.args[0] == "new-session"


def test_real_split_pane_uses_list_diff() -> None:
    with patch("agent_team.psmux_backend.shutil.which", return_value="C:\\psmux.exe"):
        backend = PsmuxBackend(mock=False)
        list_outputs = ["%0\n", "%0\n%1\n"]

        def fake_run(argv, **kwargs):
            args = argv[1:]
            if args[:2] == ["list-panes", "-t"]:
                stdout = list_outputs.pop(0)
                return MagicMock(returncode=0, stdout=stdout, stderr="")
            if args[0] == "split-window":
                return MagicMock(returncode=0, stdout="", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("agent_team.psmux_backend.subprocess.run", side_effect=fake_run):
            pane_id = backend.split_pane("sess")
        assert pane_id == "%1"


def test_recorded_calls_empty_when_not_mock() -> None:
    with patch("agent_team.psmux_backend.shutil.which", return_value="C:\\psmux.exe"):
        backend = PsmuxBackend(mock=False)
        assert backend.recorded_calls == []


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("psmux") is None, reason="psmux not installed")
def test_real_new_session_and_list() -> None:
    exe = shutil.which("psmux")
    assert exe is not None
    backend = PsmuxBackend(mock=False)
    name = "agent-team-s4-integration"
    try:
        pane_id = backend.new_session(name)
        panes = backend.list_panes(name)
        assert pane_id.startswith("%")
        assert any(p.pane_id == pane_id for p in panes)
    finally:
        subprocess.run([exe, "kill-session", "-t", name], check=False, capture_output=True)
