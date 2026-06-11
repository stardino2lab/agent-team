"""Lead context CLI commands."""

from __future__ import annotations

from pathlib import Path

import click

from agent_team.cli._helpers import CLI_ERRORS, echo_error
from agent_team.project_loader import ProjectLoader


@click.group("context")
def context_group() -> None:
    """Lead prompt preview commands."""


@context_group.command("show")
@click.option("--project", type=click.Path(path_type=Path), default=".")
@click.option("--playbook", default=None, help="Playbook name override")
def show_cmd(project: Path, playbook: str | None) -> None:
    """Preview assembled lead context."""
    try:
        loader = ProjectLoader(project.resolve())
        ctx = loader.build_lead_context(playbook_name=playbook)
        click.echo(ctx.text)
    except CLI_ERRORS as exc:
        echo_error(str(exc))
