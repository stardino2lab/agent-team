"""Task board CLI commands."""

from __future__ import annotations

import click

from agent_team.cli._helpers import CLI_ERRORS, echo_error, resolve_session_dir
from agent_team.event_log import EventLog
from agent_team.tasks import claim_task, complete_task, create_task, list_tasks


@click.group("task")
def task_group() -> None:
    """Shared task board commands."""


@task_group.command("create")
@click.option("--session", required=True)
@click.option("--title", required=True)
@click.option("--description", default="")
@click.option("--deps", default="", help="Comma-separated task IDs")
def create_cmd(session: str, title: str, description: str, deps: str) -> None:
    """Create a new task."""
    try:
        session_dir = resolve_session_dir(session)
        dep_list = [d.strip() for d in deps.split(",") if d.strip()]
        task = create_task(
            session_dir,
            title=title,
            description=description,
            deps=dep_list or None,
            event_log=EventLog(),
        )
        click.echo(task.id)
    except CLI_ERRORS as exc:
        echo_error(str(exc))


@task_group.command("list")
@click.option("--session", required=True)
def list_cmd(session: str) -> None:
    """List all tasks."""
    try:
        session_dir = resolve_session_dir(session)
        for task in list_tasks(session_dir):
            click.echo(
                f"{task.id} [{task.state}] {task.title}"
                + (f" assignee={task.assignee}" if task.assignee else "")
            )
    except CLI_ERRORS as exc:
        echo_error(str(exc))


@task_group.command("claim")
@click.option("--session", required=True)
@click.option("--id", "task_id", required=True)
@click.option("--assignee", required=True)
def claim_cmd(session: str, task_id: str, assignee: str) -> None:
    """Claim a pending task."""
    try:
        session_dir = resolve_session_dir(session)
        task = claim_task(
            session_dir,
            task_id,
            assignee,
            event_log=EventLog(),
        )
        click.echo(f"{task.id} {task.state}")
    except CLI_ERRORS as exc:
        echo_error(str(exc))


@task_group.command("complete")
@click.option("--session", required=True)
@click.option("--id", "task_id", required=True)
def complete_cmd(session: str, task_id: str) -> None:
    """Complete an in-progress task."""
    try:
        session_dir = resolve_session_dir(session)
        task = complete_task(session_dir, task_id, event_log=EventLog())
        click.echo(f"{task.id} {task.state}")
    except CLI_ERRORS as exc:
        echo_error(str(exc))
