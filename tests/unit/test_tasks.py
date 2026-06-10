"""TaskBoard unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_team._io import InvalidPathSegmentError
from agent_team.event_log import EventLog
from agent_team.tasks import (
    TaskDependencyError,
    TaskNotFoundError,
    TaskStateError,
    claim_task,
    complete_task,
    create_task,
    get_task,
    list_tasks,
)


def test_create_and_list_tasks(session_dir: Path) -> None:
    t1 = create_task(session_dir, title="First", description="desc")
    t2 = create_task(session_dir, title="Second")

    tasks = list_tasks(session_dir)
    assert len(tasks) == 2
    assert tasks[0].id == "task-001"
    assert tasks[1].id == "task-002"
    assert t1.state == "pending"
    assert t2.assignee is None


def test_claim_sets_assignee_and_state(session_dir: Path) -> None:
    task = create_task(session_dir, title="Work")
    claimed = claim_task(session_dir, task.id, assignee="implementer-1")

    assert claimed.state == "in_progress"
    assert claimed.assignee == "implementer-1"


def test_claim_blocked_by_incomplete_dep(session_dir: Path) -> None:
    dep = create_task(session_dir, title="Dependency")
    blocked = create_task(session_dir, title="Blocked", deps=[dep.id])

    with pytest.raises(TaskDependencyError):
        claim_task(session_dir, blocked.id, assignee="implementer-1")


def test_claim_after_dep_completed(session_dir: Path) -> None:
    dep = create_task(session_dir, title="Dependency")
    blocked = create_task(session_dir, title="Blocked", deps=[dep.id])

    claim_task(session_dir, dep.id, assignee="implementer-1")
    complete_task(session_dir, dep.id)
    claimed = claim_task(session_dir, blocked.id, assignee="implementer-1")
    assert claimed.state == "in_progress"


def test_complete_task(session_dir: Path) -> None:
    task = create_task(session_dir, title="Finish me")
    claim_task(session_dir, task.id, assignee="implementer-1")
    done = complete_task(session_dir, task.id)

    assert done.state == "completed"


def test_claim_non_pending_raises(session_dir: Path) -> None:
    task = create_task(session_dir, title="Work")
    claim_task(session_dir, task.id, assignee="a")

    with pytest.raises(TaskStateError):
        claim_task(session_dir, task.id, assignee="b")


def test_task_events(session_dir: Path, event_log: EventLog) -> None:
    task = create_task(session_dir, title="Evented", event_log=event_log)
    claim_task(session_dir, task.id, assignee="lead", event_log=event_log)
    complete_task(session_dir, task.id, event_log=event_log)

    events = event_log.read(session_dir)
    assert [e.type for e in events] == ["task_created", "task_claimed", "task_completed"]
    assert events[0].payload == {"task_id": task.id, "title": "Evented"}
    assert events[1].payload == {"task_id": task.id, "assignee": "lead"}
    assert events[2].payload == {"task_id": task.id}


def test_claim_missing_dep_raises(session_dir: Path) -> None:
    blocked = create_task(session_dir, title="Blocked", deps=["task-999"])
    with pytest.raises(TaskNotFoundError):
        claim_task(session_dir, blocked.id, assignee="implementer-1")


def test_complete_non_in_progress_raises(session_dir: Path) -> None:
    task = create_task(session_dir, title="Pending")
    with pytest.raises(TaskStateError):
        complete_task(session_dir, task.id)


def test_invalid_task_id_rejected(session_dir: Path) -> None:
    with pytest.raises(InvalidPathSegmentError):
        get_task(session_dir, "../evil")
