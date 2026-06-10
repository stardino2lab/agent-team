"""CLI entry point for agent-team."""

from __future__ import annotations

import click

from agent_team import __version__


@click.group()
@click.version_option(version=__version__, prog_name="agent-team")
def main() -> None:
    """Windows-native multi-agent orchestrator for Claude and Codex CLI."""


@main.command()
def version() -> None:
    """Print package version."""
    click.echo(__version__)


if __name__ == "__main__":
    main()
