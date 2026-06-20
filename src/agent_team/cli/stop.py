"""agent-team stop - gracefully stop a running session's orchestrator (S18b1/b3).

Records the terminal orchestrator_stopped event and raises a marker the running
watch loop polls for, so a backgrounded run exits gracefully (exit 0) and writes
its result manifest.

stop == TERMINATE the session, so it also REAPS the session's panes (S18b3). This
differs from an attended Ctrl-C/detach (which preserves panes for re-attach): if
the orchestrator already CRASHED it never observes the marker, so nothing else
would ever kill the orphaned auto-approve teammates — stop must reap them itself.
The reap is best-effort (no backend / already-gone session → no-op).
"""

from __future__ import annotations

import click

from agent_team.cli._helpers import (
    CLI_ERRORS,
    echo_error,
    request_stop,
    resolve_base_dir,
    resolve_session_dir,
)
from agent_team.event_log import EventLog
from agent_team.session import SessionStore
from agent_team.terminal_backend import make_terminal_backend


def _reap_orphan_panes(session_id: str, *, backend_factory=make_terminal_backend) -> None:
    """Kill the session's panes so a crashed orchestrator's teammates don't keep
    editing headless. Fully best-effort: BackendNotFoundError (a FileNotFoundError,
    NOT in CLI_ERRORS) and an already-gone session are both swallowed."""
    try:
        store = SessionStore(base_dir=resolve_base_dir())
        session = store.load(session_id)
        backend_factory().kill_session(session.psmux_session)
    except Exception:
        pass


@click.command("stop")
@click.option("--session", required=True)
def stop_cmd(session: str) -> None:
    """Gracefully stop (and terminate) a session's orchestrator."""
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
        # Reap AFTER event+marker, with its own guard — a backend error must not
        # crash stop (the terminal state is already recorded).
        _reap_orphan_panes(session)
        click.echo(f"stop requested for {session}")
    except CLI_ERRORS as exc:
        echo_error(str(exc))
