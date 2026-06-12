"""agent-team start — orchestrate a new session."""

from __future__ import annotations

import os
import threading
from pathlib import Path

import click

from agent_team.cli._helpers import echo_error
from agent_team.event_log import EventLog
from agent_team.orchestrator import Orchestrator, OrchestratorContext
from agent_team.personas import PersonaRegistry
from agent_team.project_loader import (
    PlaybookNotFoundError,
    ProjectConfigError,
    TeamMdNotFoundError,
)
from agent_team.psmux_backend import PsmuxBackend, PsmuxNotFoundError
from agent_team.session import SessionNotFoundError, SessionStore
from agent_team.spawn_approval import SpawnApproval
from agent_team.teammate_runner import TeammateRunner


@click.command("start")
@click.option(
    "--project",
    "project",
    required=True,
    type=click.Path(path_type=Path, exists=False),
    help="Project root containing .agent-team/config.yaml",
)
@click.option(
    "--session",
    "session_id",
    default=None,
    help="Session id (default: project dir name)",
)
@click.option("--playbook", default=None, help="Playbook name (overrides config default)")
@click.option("--context", "context_text", default=None, help="Extra context for lead prompt")
@click.option("--dry-run", is_flag=True, help="TeammateRunner mock — no real CLI invocation")
@click.option("--no-psmux", is_flag=True, help="Skip psmux pane creation (file + TUI only)")
@click.option(
    "--no-block",
    is_flag=True,
    hidden=True,
    help="Return immediately after starting (test seam)",
)
def start_cmd(
    project: Path,
    session_id: str | None,
    playbook: str | None,
    context_text: str | None,
    dry_run: bool,
    no_psmux: bool,
    no_block: bool,
) -> None:
    """Start a new orchestrated session."""
    project = project.resolve()
    sid = session_id or project.name
    store = SessionStore()

    try:
        store.load(sid)
        echo_error(
            f"Session already exists: {sid}. Use `agent-team attach --session {sid}`."
        )
    except SessionNotFoundError:
        pass

    try:
        psmux = PsmuxBackend(mock=no_psmux)
    except PsmuxNotFoundError as exc:
        echo_error(str(exc))

    registry = PersonaRegistry(project_path=project)
    runner = TeammateRunner(psmux, registry, mock=dry_run)
    ctx = OrchestratorContext(
        session_id=sid,
        session_dir=store.session_dir(sid),
        store=store,
        approval=SpawnApproval(),
        runner=runner,
        psmux=psmux,
        event_log=EventLog(),
        no_psmux=no_psmux,
    )
    orch = Orchestrator(ctx)
    try:
        orch.start(project_path=project, playbook=playbook, context_text=context_text)
    except (ProjectConfigError, TeamMdNotFoundError, PlaybookNotFoundError) as exc:
        echo_error(str(exc))

    click.echo(f"Session {sid} started. Do not close this shell.")

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
