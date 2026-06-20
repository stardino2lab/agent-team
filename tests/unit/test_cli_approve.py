"""`agent-team approvals` external-approver CLI (S18a)."""

from __future__ import annotations

import json

from click.testing import CliRunner

from agent_team.__main__ import main
from agent_team.event_log import EventLog
from agent_team.session import SessionStore
from agent_team.spawn_approval import SpawnApproval


def _seed_pending(store: SessionStore, sid: str = "ap") -> str:
    store.create(session_id=sid, project_path="c:\\proj", psmux_session=sid)
    session_dir = store.session_dir(sid)
    req = SpawnApproval().request_spawn(
        session_dir, persona="planner", cli="claude", prompt="plan it",
        requested_by="lead", event_log=EventLog(),
    )
    return req.request_id


def test_approve_attributes_external_approver(
    session_store: SessionStore, cli_env: dict
) -> None:
    rid = _seed_pending(session_store)
    result = CliRunner().invoke(
        main,
        ["approvals", "approve", "--session", "ap", "--id", rid, "--by", "hermes"],
        env=cli_env,
    )
    assert result.exit_code == 0, result.output
    # Same resolution + event a TUI approval would write, attributed to hermes.
    resolutions = SpawnApproval().read_resolutions(session_store.session_dir("ap"))
    assert len(resolutions) == 1
    assert resolutions[0].decision == "approved"
    assert resolutions[0].decided_by == "hermes"
    events = EventLog().read(session_store.session_dir("ap"))
    approved = [e for e in events if e.type == "spawn_approved"]
    assert approved and approved[0].payload["request_id"] == rid
    # The pending gate is cleared (so run_once would spawn exactly once).
    assert SpawnApproval().get_pending(session_store.session_dir("ap")) is None


def test_deny_writes_denied_resolution_and_event(
    session_store: SessionStore, cli_env: dict
) -> None:
    rid = _seed_pending(session_store)
    result = CliRunner().invoke(
        main, ["approvals", "deny", "--session", "ap", "--id", rid], env=cli_env
    )
    assert result.exit_code == 0, result.output
    resolutions = SpawnApproval().read_resolutions(session_store.session_dir("ap"))
    assert resolutions[0].decision == "denied"
    assert resolutions[0].decided_by == "user"  # default approver identity
    events = EventLog().read(session_store.session_dir("ap"))
    assert any(e.type == "spawn_denied" for e in events)


def test_approve_with_no_pending_exits_1(
    session_store: SessionStore, cli_env: dict
) -> None:
    session_store.create(session_id="empty", project_path="c:\\p", psmux_session="empty")
    result = CliRunner().invoke(
        main, ["approvals", "approve", "--session", "empty", "--id", "apr-001"],
        env=cli_env,
    )
    assert result.exit_code == 1  # SpawnRequestNotFoundError -> clean error, no traceback


def test_approve_wrong_request_id_exits_1(
    session_store: SessionStore, cli_env: dict
) -> None:
    _seed_pending(session_store)
    result = CliRunner().invoke(
        main, ["approvals", "approve", "--session", "ap", "--id", "apr-999"],
        env=cli_env,
    )
    assert result.exit_code == 1  # SpawnRequestMismatchError (ValueError) -> exit 1


def test_double_approve_is_idempotent_no_duplicate(
    session_store: SessionStore, cli_env: dict
) -> None:
    rid = _seed_pending(session_store)
    runner = CliRunner()
    first = runner.invoke(
        main, ["approvals", "approve", "--session", "ap", "--id", rid], env=cli_env
    )
    assert first.exit_code == 0
    second = runner.invoke(
        main, ["approvals", "approve", "--session", "ap", "--id", rid], env=cli_env
    )
    assert second.exit_code == 1  # pending already cleared -> clean error
    # No duplicate resolution appended by the retry.
    resolutions = SpawnApproval().read_resolutions(session_store.session_dir("ap"))
    assert len(resolutions) == 1


def test_approvals_list_json_shows_pending(
    session_store: SessionStore, cli_env: dict
) -> None:
    rid = _seed_pending(session_store)
    result = CliRunner().invoke(
        main, ["approvals", "list", "--session", "ap", "--json"], env=cli_env
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["pending"]["request_id"] == rid
    assert data["pending"]["persona"] == "planner"
    assert "prompt_preview" in data["pending"]
    assert "prompt" not in data["pending"]  # full prompt never exposed


def test_approvals_list_none_when_empty(
    session_store: SessionStore, cli_env: dict
) -> None:
    session_store.create(session_id="empty", project_path="c:\\p", psmux_session="empty")
    result = CliRunner().invoke(
        main, ["approvals", "list", "--session", "empty", "--json"], env=cli_env
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {"pending": None}


def test_approvals_list_unknown_session_exits_1(cli_env: dict) -> None:
    result = CliRunner().invoke(
        main, ["approvals", "list", "--session", "nope"], env=cli_env
    )
    assert result.exit_code == 1
