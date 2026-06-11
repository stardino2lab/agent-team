"""CLI entry point for agent-team."""

from __future__ import annotations

import click

from agent_team import __version__
from agent_team.cli.context import context_group
from agent_team.cli.init import init_cmd
from agent_team.cli.logs import logs_group
from agent_team.cli.mail import mail_group
from agent_team.cli.personas_cmd import personas_group
from agent_team.cli.task import task_group


@click.group()
@click.version_option(version=__version__, prog_name="agent-team")
def main() -> None:
    """Windows-native multi-agent orchestrator for Claude and Codex CLI."""


main.add_command(init_cmd)
main.add_command(mail_group)
main.add_command(task_group)
main.add_command(logs_group)
main.add_command(personas_group)
main.add_command(context_group)


@main.command()
def version() -> None:
    """Print package version."""
    click.echo(__version__)


if __name__ == "__main__":
    main()
