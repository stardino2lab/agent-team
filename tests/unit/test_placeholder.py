"""S0 scaffold smoke tests."""

from __future__ import annotations

from click.testing import CliRunner

from agent_team import __version__
from agent_team.__main__ import main


def test_version_string() -> None:
    assert __version__ == "0.1.0"


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"], prog_name="agent-team")
    assert result.exit_code == 0
    assert "agent-team" in result.output


def test_cli_version_command() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output
