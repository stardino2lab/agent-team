"""agent-team attach — resume orchestrator on an existing session."""

from __future__ import annotations

import os
import threading
from pathlib import Path

import click

from agent_team.cli._helpers import echo_error
from agent_team.event_log import EventLog
from agent_team.orchestrator import Orchestrator, OrchestratorContext
from agent_team.personas import PersonaRegistry
from agent_team.psmux_backend import PsmuxBackend, PsmuxNotFoundError
from agent_team.session import SessionNotFoundError, SessionStore
from agent_team.spawn_approval import SpawnApproval
from agent_team.teammate_runner import TeammateRunner


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
        psmux = PsmuxBackend(mock=no_psmux)
    except PsmuxNotFoundError as exc:
        echo_error(str(exc))

    project_path = Path(session.project_path)
    registry = PersonaRegistry(project_path=project_path)
    runner = TeammateRunner(psmux, registry, mock=dry_run)
    ctx = OrchestratorContext(
        session_id=session_id,
        session_dir=store.session_dir(session_id),
        store=store,
        approval=SpawnApproval(),
        runner=runner,
        psmux=psmux,
        event_log=EventLog(),
        no_psmux=no_psmux,
    )
    orch = Orchestrator(ctx)
    orch.attach()
    click.echo(f"Attached to {session_id}. Do not close this shell.")

    no_block_env = os.environ.get("AGENT_TEAM_NO_BLOCK") == "1"
    if no_block or no_block_env:
        orch.stop_watching()
        return

    stop_event = threading.Event()
    try:
        stop_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        orch.stop_watching()
