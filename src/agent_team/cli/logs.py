"""Event log CLI commands."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import click

from agent_team.cli._helpers import (
    CLI_ERRORS,
    echo_error,
    follow_once,
    follow_sleep,
    resolve_session_dir,
)
from agent_team.event_log import EventLog


@click.group("logs")
def logs_group() -> None:
    """Audit log commands."""


@logs_group.command("tail")
@click.option("--session", required=True)
@click.option("--lines", default=50, show_default=True)
@click.option("--follow", is_flag=True)
def tail_cmd(session: str, lines: int, follow: bool) -> None:
    """Show recent events."""
    try:
        session_dir = resolve_session_dir(session)
        log = EventLog()
        if not follow:
            for event in log.tail(session_dir, n=lines):
                click.echo(f"{event.ts} {event.type} {json.dumps(event.payload, default=str)}")
            return

        emitted = 0
        while True:
            events = log.read(session_dir)
            for event in events[emitted:]:
                click.echo(f"{event.ts} {event.type} {json.dumps(event.payload, default=str)}")
            emitted = len(events)
            if follow_once():
                break
            follow_sleep()
    except CLI_ERRORS as exc:
        echo_error(str(exc))


@logs_group.command("export")
@click.option("--session", required=True)
@click.option("--to", "dest", required=True, type=click.Path(path_type=Path))
def export_cmd(session: str, dest: Path) -> None:
    """Export events.jsonl to a file."""
    try:
        session_dir = resolve_session_dir(session)
        source = session_dir / "events.jsonl"
        if not source.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("", encoding="utf-8")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
        click.echo(str(dest))
    except CLI_ERRORS as exc:
        echo_error(str(exc))
