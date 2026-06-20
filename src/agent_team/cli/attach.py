"""agent-team attach - resume orchestrator on an existing session."""

from __future__ import annotations

from pathlib import Path

import click

from agent_team.cli._helpers import (
    block_until_stopped,
    clear_stop,
    echo_error,
    make_orchestrator,
)
from agent_team.psmux_backend import PsmuxCommandError, PsmuxNotFoundError
from agent_team.session import SessionNotFoundError, SessionStore
from agent_team.terminal_backend import make_terminal_backend


@click.command("attach")
@click.option("--session", "session_id", required=True, help="Session id to attach")
@click.option("--dry-run", is_flag=True, help="TeammateRunner mock")
@click.option("--no-psmux", is_flag=True, help="Skip psmux (file orchestrator only)")
@click.option("--no-block", is_flag=True, hidden=True, help="Return after attach (test seam)")
def attach_cmd(
    session_id: str,
    dry_run: bool,
    no_psmux: bool,
    no_block: bool,
) -> None:
    """Resume orchestrator watch loop on an existing session."""
    store = SessionStore()
    try:
        session = store.load(session_id)
    except SessionNotFoundError as exc:
        echo_error(str(exc))

    try:
        psmux = make_terminal_backend(mock=no_psmux)
    except PsmuxNotFoundError as exc:
        echo_error(str(exc))

    if not no_psmux:
        try:
            psmux.list_panes(session.psmux_session)
        except PsmuxCommandError as exc:
            click.echo(
                f"psmux session '{session.psmux_session}' not reachable "
                f"({exc}); falling back to file-only mode.",
                err=True,
            )
            no_psmux = True
            psmux = make_terminal_backend(mock=True)

    project_path = Path(session.project_path)
    if not project_path.exists():
        echo_error(
            f"Project path no longer exists: {project_path}. "
            f"Recreate it or update session.json."
        )

    orch = make_orchestrator(
        session_id=session_id,
        project_path=project_path,
        psmux=psmux,
        no_psmux=no_psmux,
        dry_run=dry_run,
    )
    orch.attach()
    click.echo(
        f"Attached to {session_id}. Press Ctrl-C to stop the orchestrator "
        f"(this shell drives spawn approvals; do not close it)."
    )

    # Drop any stale stop marker, then block until Ctrl-C or `agent-team stop` (S18b1).
    clear_stop(orch.ctx.session_dir)
    block_until_stopped(orch, session_id, no_block=no_block, manifest=True)
