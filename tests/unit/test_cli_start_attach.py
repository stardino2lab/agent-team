"""CLI e2e for agent-team start / attach."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from agent_team.__main__ import main
from agent_team.cli_registry import LeadCliNotSupportedError
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
    # S16b: --no-block is a test detach, not a real stop, so it must NOT write the
    # result-manifest cache (which would misleadingly imply a finished session).
    assert not (session_store.session_dir("e2e-start") / "result_manifest.json").exists()


def test_start_real_mode_renders_mcp_config_and_sends_claude_launch(
    cli_env: dict[str, str],
    minimal_project: Path,
    session_store: SessionStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """e2e: --no-psmux 빠진 real path 가 MCP config 쓰고 claude 시동 명령 보낸다.

    PsmuxBackend 가 진짜 psmux 를 부르는 대신 모든 호출을 기록만 하도록
    monkeypatch — 실제 psmux 가 PATH 에 없어도 CLI 경로 검증 가능.
    """
    # shutil is a shared module, so this also covers orchestrator's which() call
    # that resolves the lead `claude` executable. Return a per-name fake so the
    # psmux binary resolves to /fake/psmux and claude to /fake/claude.
    monkeypatch.setattr(
        "agent_team.psmux_backend.shutil.which", lambda name: f"/fake/{name}"
    )

    recorded: list[list[str]] = []

    def fake_run(self, args, *, cwd=None):  # type: ignore[no-untyped-def]
        recorded.append(list(args))
        # new_session needs a panes list afterwards; pretend session has one.
        return ""

    monkeypatch.setattr(PsmuxBackend, "_run", fake_run)
    monkeypatch.setattr(
        PsmuxBackend, "list_panes", lambda self, s: []  # noqa: ARG005
    )

    # new_session normally calls list_panes to discover the new pane id; with
    # an empty list it would raise. Short-circuit it to a stub pane id.
    def fake_new_session(self, name, *, command=None, cwd=None):  # type: ignore[no-untyped-def]
        recorded.append(["new-session", "-s", name])
        return "%0"

    monkeypatch.setattr(PsmuxBackend, "new_session", fake_new_session)

    def fake_split_pane(self, session, **kw):  # type: ignore[no-untyped-def]
        recorded.append(["split-window", "-t", session, str(kw)])
        return "%1"

    monkeypatch.setattr(PsmuxBackend, "split_pane", fake_split_pane)

    def fake_send_keys(self, target, keys, *, submit_keys=("Enter",)):  # type: ignore[no-untyped-def]
        recorded.append(["send-keys", "-t", target, "-l", keys])

    monkeypatch.setattr(PsmuxBackend, "send_keys", fake_send_keys)

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "start",
            "--project",
            str(minimal_project),
            "--session",
            "s9-e2e",
            "--no-block",
        ],
        env=cli_env,
    )
    assert result.exit_code == 0, result.output

    mcp_path = session_store.session_dir("s9-e2e") / "claude-mcp.json"
    assert mcp_path.exists()

    send_keys_lines = [r for r in recorded if r[0] == "send-keys"]
    assert send_keys_lines, "no send-keys recorded"
    payload = send_keys_lines[0][-1]
    # First token is the resolved claude executable (bare name or full path).
    assert "claude" in payload.split()[0].lower()
    assert "--mcp-config" in payload
    assert "--strict-mcp-config" in payload
    assert "--append-system-prompt-file" in payload
    assert "lead-system-prompt.md" in payload


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


def test_start_unsupported_lead_cli_reports_clean_error(
    cli_env: dict[str, str],
    tmp_path: Path,
) -> None:
    """A lead_cli the registry rejects must echo a clean error, not a traceback.

    Regression: start_cmd's except tuple did not include LeadCliNotSupportedError,
    so an unsupported lead_cli propagated a raw Python traceback to the user
    instead of the guidance message the orchestrator raises. codex is now a
    supported lead (S11c), so antigravity stands in as the still-unsupported one.
    """
    proj = tmp_path / "antigravity-lead"
    (proj / ".agent-team").mkdir(parents=True)
    (proj / ".agent-team" / "config.yaml").write_text(
        "project_name: antigravity-lead\nmax_teammates: 2\nlead_cli: antigravity\n",
        encoding="utf-8",
    )
    (proj / "TEAM.md").write_text("# Team\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["start", "--project", str(proj), "--session", "antigravity-lead",
         "--no-psmux", "--no-block"],
        env=cli_env,
    )
    assert result.exit_code != 0
    # The clean guidance message reached the user (stderr), not a stack trace.
    combined = result.output + (result.stderr or "")
    assert "S12" in combined
    assert not isinstance(result.exception, LeadCliNotSupportedError)


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
    # Per-name fake also covers orchestrator resolving the lead claude binary.
    monkeypatch.setattr(
        "agent_team.psmux_backend.shutil.which", lambda name: f"/fake/{name}"
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
    # S10b: attach drains + spawns the teammate as "starting"; teammate_ready is
    # deferred until the teammate writes its ready marker (none in this dry-run).
    assert teammates[0].status == "starting"
    assert teammates[0].request_id is not None
