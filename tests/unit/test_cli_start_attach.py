"""CLI e2e for agent-team start / attach."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from agent_team.__main__ import main
from agent_team.event_log import EventLog
from agent_team.psmux_backend import PsmuxBackend, PsmuxCommandError
from agent_team.session import SessionStore
from agent_team.spawn_approval import SpawnApproval


def test_start_cli_dry_run_creates_session(
    cli_env: dict[str, str],
    consumer_project: Path,
    session_store: SessionStore,
) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "start",
            "--project",
            str(consumer_project),
            "--session",
            "e2e-start",
            "--dry-run",
            "--no-psmux",
            "--no-block",
        ],
        env=cli_env,
    )
    assert result.exit_code == 0, result.output
    assert "Session e2e-start started" in result.output

    session = session_store.load("e2e-start")
    assert session.members[0].name == "lead"

    events = EventLog().read(session_store.session_dir("e2e-start"))
    assert any(e.type == "session_started" for e in events)
    assert any(e.type == "orchestrator_stopped" for e in events)


def test_start_refuses_when_session_exists(
    cli_env: dict[str, str],
    consumer_project: Path,
    session_store: SessionStore,
) -> None:
    session_store.create(
        session_id="dup",
        project_path=str(consumer_project),
        psmux_session="dup",
    )
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "start",
            "--project",
            str(consumer_project),
            "--session",
            "dup",
            "--dry-run",
            "--no-psmux",
            "--no-block",
        ],
        env=cli_env,
    )
    assert result.exit_code != 0
    assert "already exists" in result.output or "already exists" in (result.stderr or "")


def test_attach_errors_when_project_path_missing(
    cli_env: dict[str, str],
    session_store: SessionStore,
    tmp_path: Path,
) -> None:
    gone = tmp_path / "vanished"
    sid = "stale-path"
    session_store.create(
        session_id=sid,
        project_path=str(gone),
        psmux_session=sid,
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["attach", "--session", sid, "--dry-run", "--no-psmux", "--no-block"],
        env=cli_env,
    )
    assert result.exit_code != 0
    combined = result.output + (result.stderr or "")
    assert "no longer exists" in combined


def test_attach_falls_back_when_psmux_session_missing(
    cli_env: dict[str, str],
    consumer_project: Path,
    session_store: SessionStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sid = "stale-psmux"
    session_store.create(
        session_id=sid,
        project_path=str(consumer_project),
        psmux_session="ghost",
    )

    # Pretend psmux is installed so PsmuxBackend(mock=False) constructs cleanly.
    monkeypatch.setattr(
        "agent_team.psmux_backend.shutil.which", lambda _x: "/fake/psmux"
    )

    def boom(self, _session):  # type: ignore[no-untyped-def]
        raise PsmuxCommandError(
            "no such session",
            exit_code=1,
            command_args=["list-panes"],
            stderr="no such session",
        )

    monkeypatch.setattr(PsmuxBackend, "list_panes", boom)

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["attach", "--session", sid, "--dry-run", "--no-block"],
        env=cli_env,
    )
    assert result.exit_code == 0, result.output
    combined = result.output + (result.stderr or "")
    assert "not reachable" in combined and "file-only" in combined


def test_attach_cli_resumes_and_drains_pending_resolutions(
    cli_env: dict[str, str],
    consumer_project: Path,
    session_store: SessionStore,
) -> None:
    sid = "e2e-attach"
    session_store.create(
        session_id=sid,
        project_path=str(consumer_project),
        psmux_session=sid,
    )
    # Pre-queue an approved spawn (before attach)
    approval = SpawnApproval()
    event_log = EventLog()
    session_dir = session_store.session_dir(sid)
    req = approval.request_spawn(
        session_dir,
        persona="planner",
        cli="claude",
        prompt="ping",
        requested_by="lead",
        event_log=event_log,
    )
    approval.approve(session_dir, req.request_id, decided_by="user", event_log=event_log)

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "attach",
            "--session",
            sid,
            "--dry-run",
            "--no-psmux",
            "--no-block",
        ],
        env=cli_env,
    )
    assert result.exit_code == 0, result.output

    session = session_store.load(sid)
    teammates = [m for m in session.members if m.role == "teammate"]
    assert len(teammates) == 1, [m.name for m in session.members]
    events = EventLog().read(session_dir)
    assert any(e.type == "teammate_ready" for e in events)
