"""agent-team start - orchestrate a new session."""

from __future__ import annotations

from pathlib import Path

import click

from agent_team.cli._helpers import (
    block_until_stopped,
    clear_stop,
    echo_error,
    make_orchestrator,
)
from agent_team.cli_registry import LeadCliNotSupportedError
from agent_team.project_loader import (
    PlaybookNotFoundError,
    ProjectConfigError,
    TeamMdNotFoundError,
)
from agent_team.psmux_backend import PsmuxNotFoundError
from agent_team.session import SessionExistsError, SessionNotFoundError, SessionStore
from agent_team.terminal_backend import make_terminal_backend


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
@click.option("--dry-run", is_flag=True, help="TeammateRunner mock - no real CLI invocation")
@click.option("--no-psmux", is_flag=True, help="Skip psmux pane creation (file + TUI only)")
@click.option(
    "--timeout",
    "timeout_s",
    type=float,
    default=None,
    help="Stop after N seconds (the primary liveness backstop). Kills all panes "
    "on expiry. Required with --autonomous.",
)
@click.option(
    "--autonomous",
    is_flag=True,
    help="Headless mode (no human at the TUI): --timeout is mandatory and every "
    "pane is killed on terminal stop.",
)
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
    timeout_s: float | None,
    autonomous: bool,
    no_block: bool,
) -> None:
    """Start a new orchestrated session."""
    project = project.resolve()
    sid = session_id or project.name
    # Fail fast BEFORE spawning any panes: autonomous mode has no human backstop,
    # so a wall-clock timeout is mandatory (covers the ~6 hang paths the safety
    # review found: unresolved approval, wait_for_event stall, dead teammate, ...).
    if autonomous and timeout_s is None:
        echo_error("--autonomous requires --timeout <seconds> (the liveness backstop).")
    store = SessionStore()

    try:
        store.load(sid)
        echo_error(
            f"Session already exists: {sid}. Use `agent-team attach --session {sid}`."
        )
    except SessionNotFoundError:
        pass

    try:
        psmux = make_terminal_backend(mock=no_psmux)
    except PsmuxNotFoundError as exc:
        echo_error(str(exc))

    orch = make_orchestrator(
        session_id=sid,
        project_path=project,
        psmux=psmux,
        no_psmux=no_psmux,
        dry_run=dry_run,
    )
    try:
        orch.start(project_path=project, playbook=playbook, context_text=context_text)
    except (
        ProjectConfigError,
        TeamMdNotFoundError,
        PlaybookNotFoundError,
        LeadCliNotSupportedError,
        SessionExistsError,
    ) as exc:
        echo_error(str(exc))

    click.echo(
        f"Session {sid} started. Press Ctrl-C to stop the orchestrator "
        f"(this shell drives spawn approvals; do not close it)."
    )

    # Drop any stale stop marker from a prior run so this fresh start doesn't
    # exit instantly; then block until Ctrl-C, `agent-team stop`, or --timeout
    # (S18b1/S18b2). Autonomous runs kill all panes on terminal stop.
    clear_stop(orch.ctx.session_dir)
    block_until_stopped(
        orch, sid, no_block=no_block, manifest=True,
        timeout=timeout_s, kill_panes=autonomous,
    )
