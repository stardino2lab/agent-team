"""Personas CLI commands."""

from __future__ import annotations

from pathlib import Path

import click

from agent_team.cli._helpers import CLI_ERRORS, echo_error
from agent_team.personas import PersonaRegistry


@click.group("personas")
def personas_group() -> None:
    """Persona catalog commands."""


@personas_group.command("list")
@click.option("--project", type=click.Path(path_type=Path), default=None)
def list_cmd(project: Path | None) -> None:
    """List available personas."""
    try:
        registry = PersonaRegistry(project_path=project)
        for persona in registry.list_personas():
            click.echo(f"{persona.name} ({persona.cli}): {persona.description}")
    except CLI_ERRORS as exc:
        echo_error(str(exc))
