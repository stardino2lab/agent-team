"""Shared task board with dependency blocking."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agent_team._io import format_ts, read_json, safe_segment, utc_now, write_json
from agent_team.event_log import EventLog

TaskState = Literal["pending", "in_progress", "completed"]

_TASK_ID_PATTERN = re.compile(r"^task-(\d+)\.json$")


class TaskNotFoundError(FileNotFoundError):
    """Raised when a task file does not exist."""


class TaskDependencyError(ValueError):
    """Raised when task dependencies are not satisfied."""


class TaskStateError(ValueError):
    """Raised on invalid task state transitions."""


@dataclass
class Task:
    id: str
    title: str
    description: str
    state: TaskState
    deps: list[str]
    assignee: str | None
    created_at: str
    updated_at: str


def _task_to_dict(task: Task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "state": task.state,
        "deps": task.deps,
        "assignee": task.assignee,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def _task_from_dict(data: dict) -> Task:
    return Task(
        id=data["id"],
        title=data["title"],
        description=data["description"],
        state=data["state"],
        deps=data.get("deps", []),
        assignee=data.get("assignee"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def _tasks_dir(session_dir: Path) -> Path:
    return session_dir / "tasks"


def _task_path(session_dir: Path, task_id: str) -> Path:
    safe_segment(task_id, "task_id")
    return _tasks_dir(session_dir) / f"{task_id}.json"


def _next_task_id(session_dir: Path) -> str:
    tasks_dir = _tasks_dir(session_dir)
    tasks_dir.mkdir(parents=True, exist_ok=True)
    max_num = 0
    for path in tasks_dir.iterdir():
        match = _TASK_ID_PATTERN.match(path.name)
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"task-{max_num + 1:03d}"


def create_task(
    session_dir: Path,
    *,
    title: str,
    description: str = "",
    deps: list[str] | None = None,
    event_log: EventLog | None = None,
) -> Task:
    now = format_ts(utc_now())
    task_id = _next_task_id(session_dir)
    task = Task(
        id=task_id,
        title=title,
        description=description,
        state="pending",
        deps=deps or [],
        assignee=None,
        created_at=now,
        updated_at=now,
    )
    write_json(_task_path(session_dir, task_id), _task_to_dict(task))

    if event_log is not None:
        event_log.append(
            session_dir,
            type_="task_created",
            payload={"task_id": task.id, "title": task.title},
        )
    return task


def list_tasks(session_dir: Path) -> list[Task]:
    tasks_dir = _tasks_dir(session_dir)
    if not tasks_dir.exists():
        return []
    tasks: list[Task] = []
    for path in sorted(tasks_dir.glob("task-*.json")):
        tasks.append(_task_from_dict(read_json(path)))
    return tasks


def get_task(session_dir: Path, task_id: str) -> Task:
    path = _task_path(session_dir, task_id)
    if not path.exists():
        raise TaskNotFoundError(f"Task not found: {task_id}")
    return _task_from_dict(read_json(path))


def claim_task(
    session_dir: Path,
    task_id: str,
    assignee: str,
    event_log: EventLog | None = None,
) -> Task:
    task = get_task(session_dir, task_id)
    if task.state != "pending":
        raise TaskStateError(f"Cannot claim task in state {task.state}")

    for dep_id in task.deps:
        dep = get_task(session_dir, dep_id)
        if dep.state != "completed":
            raise TaskDependencyError(f"Dependency not completed: {dep_id}")

    task.assignee = assignee
    task.state = "in_progress"
    task.updated_at = format_ts(utc_now())
    write_json(_task_path(session_dir, task_id), _task_to_dict(task))

    if event_log is not None:
        event_log.append(
            session_dir,
            type_="task_claimed",
            payload={"task_id": task.id, "assignee": assignee},
        )
    return task


def complete_task(
    session_dir: Path,
    task_id: str,
    event_log: EventLog | None = None,
) -> Task:
    task = get_task(session_dir, task_id)
    if task.state != "in_progress":
        raise TaskStateError(f"Cannot complete task in state {task.state}")

    task.state = "completed"
    task.updated_at = format_ts(utc_now())
    write_json(_task_path(session_dir, task_id), _task_to_dict(task))

    if event_log is not None:
        event_log.append(
            session_dir,
            type_="task_completed",
            payload={"task_id": task.id},
        )
    return task
