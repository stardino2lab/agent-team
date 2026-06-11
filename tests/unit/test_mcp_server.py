"""Unit tests for MCP server handlers."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from agent_team import tasks
from agent_team._io import InvalidPathSegmentError, format_ts, parse_ts
from agent_team.event_log import EventLog
from agent_team.mcp_server import (
    McpConfigError,
    McpContext,
    McpToolError,
    _run_tool,
    handle_claim_task,
    handle_complete_task,
    handle_create_task,
    handle_list_personas,
    handle_list_teammates,
    handle_read_messages,
    handle_send_message,
    handle_shutdown_teammate,
    handle_spawn_teammate,
    resolve_context,
)
from agent_team.personas import PersonaRegistry
from agent_team.psmux_backend import PsmuxBackend
from agent_team.session import Member, SessionStore
from agent_team.spawn_approval import SpawnApproval, SpawnPendingError


def test_list_personas_filters_allowed(
    mcp_context: McpContext,
    empty_global_personas: Path,
) -> None:
    extra = mcp_context.project_path / ".agent-team" / "personas" / "extra.yaml"
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_text(
        "name: extra\ncli: claude\ndescription: not allowed\n"
        "spawn_prompt_template: x\n",
        encoding="utf-8",
    )
    mcp_context.registry = PersonaRegistry(
        project_path=mcp_context.project_path,
        global_dir=empty_global_personas,
    )
    result = handle_list_personas(mcp_context)
    names = {p["name"] for p in result["personas"]}
    assert names == {"planner", "implementer", "reviewer", "tester"}
    assert "extra" not in names


def test_spawn_teammate_pending_and_event(mcp_context: McpContext) -> None:
    result = handle_spawn_teammate(
        mcp_context,
        persona="planner",
        prompt="Plan the feature",
        name="planner-1",
    )
    assert result == {"request_id": "apr-001", "status": "pending"}
    pending_path = mcp_context.session_dir / "approval" / "pending.json"
    assert pending_path.exists()
    events = mcp_context.event_log.read(mcp_context.session_dir)
    spawn_events = [e for e in events if e.type == "spawn_requested"]
    assert len(spawn_events) == 1
    assert spawn_events[0].payload["request_id"] == "apr-001"
    assert spawn_events[0].payload["persona"] == "planner"
    assert spawn_events[0].payload["requested_by"] == "lead"


def test_spawn_teammate_disallowed_persona(mcp_context: McpContext) -> None:
    with pytest.raises(McpToolError, match="not allowed"):
        handle_spawn_teammate(mcp_context, persona="nonexistent-persona", prompt="x")


def test_spawn_teammate_duplicate_pending(mcp_context: McpContext) -> None:
    handle_spawn_teammate(mcp_context, persona="planner", prompt="first")
    with pytest.raises(SpawnPendingError):
        handle_spawn_teammate(mcp_context, persona="planner", prompt="second")


def test_list_teammates(mcp_context: McpContext) -> None:
    result = handle_list_teammates(mcp_context)
    names = {m["name"] for m in result["members"]}
    assert names == {"lead", "helper-1"}
    assert result["members"][0]["status"] == "running"


def test_send_message(mcp_context: McpContext) -> None:
    result = handle_send_message(mcp_context, to="helper-1", body="hello")
    assert result["to"] == "helper-1"
    assert result["id"]
    assert result["ts"].endswith("Z")
    inbox = mcp_context.session_dir / "mailbox" / "helper-1.jsonl"
    assert inbox.exists()
    events = mcp_context.event_log.read(mcp_context.session_dir)
    assert any(e.type == "mail_sent" for e in events)


def test_read_messages_since_filter(mcp_context: McpContext) -> None:
    handle_send_message(mcp_context, to="lead", body="old")
    handle_send_message(mcp_context, to="lead", body="new")
    all_messages = handle_read_messages(mcp_context)["messages"]
    assert len(all_messages) == 2
    early = parse_ts(all_messages[0]["ts"]) - timedelta(seconds=10)
    assert len(handle_read_messages(mcp_context, since=format_ts(early))["messages"]) == 2
    late = parse_ts(all_messages[1]["ts"]) + timedelta(seconds=10)
    assert handle_read_messages(mcp_context, since=format_ts(late))["messages"] == []


def test_create_task(mcp_context: McpContext) -> None:
    result = handle_create_task(mcp_context, title="Ship it")
    assert result["state"] == "pending"
    task_path = mcp_context.session_dir / "tasks" / f"{result['task_id']}.json"
    assert task_path.exists()
    events = mcp_context.event_log.read(mcp_context.session_dir)
    assert any(e.type == "task_created" for e in events)


def test_claim_task_default_assignee(mcp_context: McpContext) -> None:
    created = handle_create_task(mcp_context, title="Work")
    result = handle_claim_task(mcp_context, created["task_id"])
    assert result["assignee"] == "lead"
    assert result["state"] == "in_progress"
    events = mcp_context.event_log.read(mcp_context.session_dir)
    claimed = [e for e in events if e.type == "task_claimed"]
    assert claimed[-1].payload == {"task_id": created["task_id"], "assignee": "lead"}


def test_claim_task_deps_blocked(mcp_context: McpContext) -> None:
    first = handle_create_task(mcp_context, title="First")
    second = handle_create_task(
        mcp_context,
        title="Second",
        deps=[first["task_id"]],
    )
    with pytest.raises(tasks.TaskDependencyError):
        handle_claim_task(mcp_context, second["task_id"])


def test_complete_task(mcp_context: McpContext) -> None:
    created = handle_create_task(mcp_context, title="Done")
    handle_claim_task(mcp_context, created["task_id"])
    result = handle_complete_task(mcp_context, created["task_id"])
    assert result["state"] == "completed"
    events = mcp_context.event_log.read(mcp_context.session_dir)
    assert any(e.type == "task_completed" for e in events)


def test_shutdown_teammate_kill_pane_and_event(mcp_context: McpContext) -> None:
    result = handle_shutdown_teammate(mcp_context, "helper-1")
    assert result == {"name": "helper-1", "status": "shutdown"}
    assert mcp_context.psmux.recorded_calls
    session = mcp_context.store.load(mcp_context.session_id)
    assert all(m.name != "helper-1" for m in session.members)
    events = mcp_context.event_log.read(mcp_context.session_dir)
    assert any(e.type == "teammate_shutdown" for e in events)


def test_shutdown_teammate_no_pane_id(
    session_store: SessionStore,
    consumer_project: Path,
    psmux_backend: PsmuxBackend,
    event_log: EventLog,
    empty_global_personas: Path,
) -> None:
    session = session_store.create(
        session_id="no-pane",
        project_path=str(consumer_project),
        psmux_session="no-pane",
        members=[
            Member(
                name="lead",
                role="lead",
                persona=None,
                cli="claude",
                pane_id=None,
                backend="psmux",
                status="running",
            ),
            Member(
                name="ghost",
                role="teammate",
                persona="planner",
                cli="claude",
                pane_id=None,
                backend="psmux",
                status="running",
            ),
        ],
    )
    ctx = McpContext(
        session_id=session.session_id,
        session_dir=session_store.session_dir(session.session_id),
        project_path=consumer_project,
        store=session_store,
        registry=PersonaRegistry(
            project_path=consumer_project,
            global_dir=empty_global_personas,
        ),
        approval=SpawnApproval(),
        psmux=psmux_backend,
        event_log=event_log,
    )
    handle_shutdown_teammate(ctx, "ghost")
    assert not psmux_backend.recorded_calls
    session = session_store.load(session.session_id)
    assert all(m.name != "ghost" for m in session.members)


def test_shutdown_teammate_lead_not_found(mcp_context: McpContext) -> None:
    with pytest.raises(McpToolError, match="not found"):
        handle_shutdown_teammate(mcp_context, "lead")


def test_spawn_teammate_max_teammates(
    session_store: SessionStore,
    consumer_project: Path,
    psmux_backend: PsmuxBackend,
    event_log: EventLog,
    empty_global_personas: Path,
) -> None:
    session = session_store.create(
        session_id="full-team",
        project_path=str(consumer_project),
        psmux_session="full-team",
        max_teammates=1,
        members=[
            Member(
                name="lead",
                role="lead",
                persona=None,
                cli="claude",
                pane_id="%0",
                backend="psmux",
                status="running",
            ),
            Member(
                name="only-one",
                role="teammate",
                persona="planner",
                cli="claude",
                pane_id="%1",
                backend="psmux",
                status="running",
            ),
        ],
    )
    ctx = McpContext(
        session_id=session.session_id,
        session_dir=session_store.session_dir(session.session_id),
        project_path=consumer_project,
        store=session_store,
        registry=PersonaRegistry(
            project_path=consumer_project,
            global_dir=empty_global_personas,
        ),
        approval=SpawnApproval(),
        psmux=psmux_backend,
        event_log=event_log,
    )
    with pytest.raises(McpToolError, match="Max teammates"):
        handle_spawn_teammate(ctx, persona="planner", prompt="x")


def test_require_project_missing(mcp_context: McpContext) -> None:
    mcp_context.project_path = None
    with pytest.raises(McpConfigError, match="AGENT_TEAM_PROJECT_PATH"):
        handle_list_personas(mcp_context)
    with pytest.raises(McpConfigError, match="AGENT_TEAM_PROJECT_PATH"):
        handle_spawn_teammate(mcp_context, persona="planner", prompt="x")


def test_read_messages_invalid_since(mcp_context: McpContext) -> None:
    handle_send_message(mcp_context, to="lead", body="seed")
    with pytest.raises(ValueError):
        handle_read_messages(mcp_context, since="not-an-iso-timestamp")


def test_send_message_bad_recipient(mcp_context: McpContext) -> None:
    with pytest.raises(InvalidPathSegmentError):
        handle_send_message(mcp_context, to="../evil", body="x")


def test_claim_task_not_found(mcp_context: McpContext) -> None:
    with pytest.raises(tasks.TaskNotFoundError):
        handle_claim_task(mcp_context, "task-999")


def test_resolve_context_missing_session_id(
    session_store: SessionStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGENT_TEAM_SESSION_ID", raising=False)
    with pytest.raises(McpConfigError, match="AGENT_TEAM_SESSION_ID"):
        resolve_context(store=session_store)


def test_run_tool_maps_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENT_TEAM_SESSION_ID", raising=False)
    with pytest.raises(RuntimeError, match="AGENT_TEAM_SESSION_ID"):
        _run_tool(handle_list_teammates)
