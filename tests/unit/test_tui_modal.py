"""TUI spawn modal handler tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_team.event_log import EventLog
from agent_team.spawn_approval import SpawnApproval, SpawnRequestNotFoundError
from agent_team.tui.context import TuiContext, resolve_tui_context
from agent_team.tui.modal import handle_approve, handle_deny


@pytest.fixture
def modal_ctx(
    tui_session_dir: Path,
    session_store,
    event_log: EventLog,
) -> TuiContext:
    return resolve_tui_context(
        session_id="tui-test",
        store=session_store,
        approval=SpawnApproval(),
        event_log=event_log,
    )


def test_handle_approve_writes_resolution_and_event(modal_ctx: TuiContext) -> None:
    req = modal_ctx.approval.request_spawn(
        modal_ctx.session_dir,
        persona="planner",
        cli="claude",
        prompt="Plan it",
        requested_by="lead",
        teammate_name="helper-2",
        event_log=modal_ctx.event_log,
    )

    resolution = handle_approve(modal_ctx, req.request_id)
    assert resolution.decision == "approved"
    assert resolution.decided_by == "user"
    assert modal_ctx.approval.get_pending(modal_ctx.session_dir) is None

    events = modal_ctx.event_log.read(modal_ctx.session_dir)
    assert events[-1].type == "spawn_approved"
    assert events[-1].payload == {"request_id": "apr-001", "persona": "planner"}


def test_handle_deny_minimal_resolution(modal_ctx: TuiContext) -> None:
    req = modal_ctx.approval.request_spawn(
        modal_ctx.session_dir,
        persona="planner",
        cli="claude",
        prompt="x",
        requested_by="lead",
        event_log=modal_ctx.event_log,
    )

    resolution = handle_deny(modal_ctx, req.request_id)
    assert resolution.decision == "denied"
    assert resolution.decided_by == "user"
    assert resolution.persona is None
    assert resolution.prompt is None

    events = modal_ctx.event_log.read(modal_ctx.session_dir)
    assert events[-1].type == "spawn_denied"
    assert events[-1].payload == {"request_id": "apr-001"}


def test_handle_approve_without_pending_raises(modal_ctx: TuiContext) -> None:
    with pytest.raises(SpawnRequestNotFoundError):
        handle_approve(modal_ctx, "apr-001")
