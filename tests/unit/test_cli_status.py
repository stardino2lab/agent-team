"""`agent-team status` CLI (S14a)."""

from __future__ import annotations

import json

from click.testing import CliRunner

from agent_team.__main__ import main
from agent_team.session import Member, SessionStore


def _seed(store: SessionStore, sid: str, *, status: str = "running") -> None:
    store.create(
        session_id=sid,
        project_path="c:\\x",
        psmux_session=sid,
        members=[
            Member(
                name="lead",
                role="lead",
                persona=None,
                cli="claude",
                pane_id="%0",
                backend="psmux",
                status=status,
            )
        ],
    )


def test_status_json_no_panes(session_store: SessionStore, cli_env: dict) -> None:
    _seed(session_store, "st")
    result = CliRunner().invoke(
        main, ["status", "--session", "st", "--no-panes", "--json"], env=cli_env
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["session_id"] == "st"
    assert data["panes_available"] is False
    # running member, pane set, liveness unavailable -> unknown (never invented-dead)
    assert data["members"][0]["health"] == "unknown"
    assert data["overall_ok"] is True


def test_status_text_renders(session_store: SessionStore, cli_env: dict) -> None:
    _seed(session_store, "st")
    result = CliRunner().invoke(
        main, ["status", "--session", "st", "--no-panes"], env=cli_env
    )
    assert result.exit_code == 0, result.output
    assert "session st" in result.output
    assert "lead" in result.output


def test_status_exit_2_when_member_error(
    session_store: SessionStore, cli_env: dict
) -> None:
    _seed(session_store, "st2", status="error")
    result = CliRunner().invoke(
        main, ["status", "--session", "st2", "--no-panes"], env=cli_env
    )
    assert result.exit_code == 2  # ran fine, team unhealthy


def test_status_unknown_session_exits_1(cli_env: dict) -> None:
    result = CliRunner().invoke(
        main, ["status", "--session", "nope", "--no-panes"], env=cli_env
    )
    assert result.exit_code == 1  # command/usage error, not a health verdict


def test_status_json_field_set_pinned(session_store: SessionStore, cli_env: dict) -> None:
    # Freeze the --json contract so S14b/S14c/S16/S18 consumers don't silently break.
    _seed(session_store, "st")
    result = CliRunner().invoke(
        main, ["status", "--session", "st", "--no-panes", "--json"], env=cli_env
    )
    data = json.loads(result.output)
    assert set(data) == {
        "session_id", "session_status", "panes_available", "overall_ok",
        "escalations", "members", "spawn_errors", "task_counts", "pending_approval",
    }
    assert set(data["members"][0]) == {
        "name", "role", "cli", "status", "pane_id", "health", "last_activity",
    }


def test_status_dead_pane_exits_2(
    session_store: SessionStore, cli_env: dict, monkeypatch
) -> None:
    # Live-panes path: a backend reporting an empty pane set -> lead %0 is DEAD ->
    # overall_ok False -> exit 2 (exercises status_cmd's real list_panes->dead seam).
    _seed(session_store, "st3")

    class _EmptyBackend:
        def list_panes(self, _session):
            return []

    monkeypatch.setattr(
        "agent_team.cli.status.make_terminal_backend", lambda: _EmptyBackend()
    )
    result = CliRunner().invoke(main, ["status", "--session", "st3"], env=cli_env)
    assert result.exit_code == 2
