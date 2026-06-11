"""TUI command."""

from __future__ import annotations

import click

from agent_team.cli._helpers import echo_error
from agent_team.session import SessionNotFoundError
from agent_team.tui.app import AgentTeamApp
from agent_team.tui.context import TuiConfigError, resolve_tui_context


@click.command("tui")
@click.option("--session", default=None, help="Session id (or AGENT_TEAM_SESSION_ID)")
def tui_cmd(session: str | None) -> None:
    """Launch Textual TUI for a session."""
    try:
        ctx = resolve_tui_context(session_id=session)
    except (TuiConfigError, SessionNotFoundError) as exc:
        echo_error(str(exc))
    AgentTeamApp(ctx).run()
