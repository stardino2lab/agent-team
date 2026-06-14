"""Teammate-side CLI commands (run by a spawned teammate)."""

from __future__ import annotations

import click

from agent_team._io import format_ts, safe_segment, utc_now, write_json
from agent_team.cli._helpers import CLI_ERRORS, echo_error, resolve_session_dir


@click.group("teammate")
def teammate_group() -> None:
    """Commands a spawned teammate runs to coordinate with the orchestrator."""


@teammate_group.command("ready")
@click.option("--session", required=True, help="Session ID")
@click.option("--as", "as_name", required=True, help="Teammate name")
def ready_cmd(session: str, as_name: str) -> None:
    """Signal that this teammate has read its brief and is ready to work.

    Writes a marker file the orchestrator polls. The orchestrator — the single
    event-log writer — emits the teammate_ready event when it sees the marker.
    Idempotent: re-running just overwrites the marker.
    """
    try:
        session_dir = resolve_session_dir(session)
        safe_segment(as_name, "teammate")
        marker = session_dir / "teammates" / as_name / "ready"
        marker.parent.mkdir(parents=True, exist_ok=True)
        write_json(marker, {"name": as_name, "ts": format_ts(utc_now())})
        click.echo(str(marker))
    except CLI_ERRORS as exc:
        echo_error(str(exc))
