"""agent-team stop - gracefully stop a running session's orchestrator (S18b1).

Lets Hermes (or a human) end a backgrounded `start`/`attach` run cleanly without
Ctrl-C: records the terminal orchestrator_stopped event and raises a marker the
running watch loop polls for, so the run exits gracefully (exit 0) and writes its
result manifest.
"""

from __future__ import annotations

import click

from agent_team.cli._helpers import (
    CLI_ERRORS,
    echo_error,
    request_stop,
    resolve_session_dir,
)
from agent_team.event_log import EventLog


@click.command("stop")
@click.option("--session", required=True)
def stop_cmd(session: str) -> None:
    """Gracefully stop a running session's orchestrator."""
    try:
        session_dir = resolve_session_dir(session)
        # Record the terminal event FIRST, THEN raise the marker: a running
        # orchestrator that observes the marker and rebuilds its manifest must
        # already see orchestrator_stopped (so session_stopped=True), not race it.
        EventLog().append(
            session_dir,
            type_="orchestrator_stopped",
            payload={"session_id": session, "reason": "stopped"},
        )
        request_stop(session_dir)
        click.echo(f"stop requested for {session}")
    except CLI_ERRORS as exc:
        echo_error(str(exc))
