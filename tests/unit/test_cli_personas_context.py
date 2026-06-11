"""CLI personas and context command tests."""

from __future__ import annotations

from click.testing import CliRunner

from agent_team.__main__ import main


def test_personas_list(consumer_project) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["personas", "list", "--project", str(consumer_project)],
    )
    assert result.exit_code == 0
    assert "planner" in result.output


def test_context_show(consumer_project) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["context", "show", "--project", str(consumer_project)],
    )
    assert result.exit_code == 0
    assert "--- TEAM.md ---" in result.output
    assert "payment-api" in result.output
