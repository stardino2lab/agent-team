"""escalation.py: read-time escalation derivation (S14c)."""

from __future__ import annotations

from agent_team.escalation import derive_escalations
from agent_team.health import MemberHealth, SessionHealth, SpawnError
from agent_team.tasks import Task


def _health(members, spawn_errors=None) -> SessionHealth:
    return SessionHealth(
        session_id="s",
        session_status="active",
        members=members,
        spawn_errors=spawn_errors or [],
        task_counts={},
        pending_approval=None,
        panes_available=True,
        overall_ok=True,
    )


def _member(name, health) -> MemberHealth:
    return MemberHealth(
        name=name, role="teammate", cli="codex", status="running",
        pane_id="%1", health=health, last_activity=None,
    )


def _task(tid, state, assignee) -> Task:
    return Task(
        id=tid, title="t", description="", state=state, deps=[],
        assignee=assignee, created_at="t", updated_at="t",
    )


def test_teammate_escalation_for_dead_and_stale() -> None:
    health = _health([_member("h1", "dead"), _member("h2", "stale"), _member("h3", "healthy")])
    esc = derive_escalations(health, [])
    levels = {(e.level, e.subject) for e in esc}
    assert ("teammate", "h1") in levels
    assert ("teammate", "h2") in levels
    assert all(e.subject != "h3" for e in esc)


def test_task_escalation_when_assignee_unhealthy() -> None:
    health = _health([_member("h1", "dead")])
    tasks = [_task("task-1", "in_progress", "h1"), _task("task-2", "in_progress", "h-ok")]
    esc = derive_escalations(health, tasks)
    task_esc = [e for e in esc if e.level == "task"]
    assert len(task_esc) == 1 and task_esc[0].subject == "task-1"


def test_user_escalation_from_spawn_errors() -> None:
    health = _health([], spawn_errors=[SpawnError(request_id="apr-9", kind="spawn_failed")])
    esc = derive_escalations(health, [])
    user = [e for e in esc if e.level == "user"]
    assert len(user) == 1 and user[0].subject == "apr-9"


def test_no_escalations_when_healthy() -> None:
    health = _health([_member("h1", "healthy"), _member("h2", "unknown")])
    assert derive_escalations(health, [_task("task-1", "in_progress", "h1")]) == []
