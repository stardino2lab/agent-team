"""CLI task command tests."""

from __future__ import annotations

from click.testing import CliRunner

from agent_team.__main__ import main
from agent_team.session import SessionStore


def test_task_lifecycle(cli_env: dict, session_store: SessionStore) -> None:
    session_store.create(
        session_id="cli-task",
        project_path="c:\\DEV\\test",
        psmux_session="cli-task",
    )
    runner = CliRunner()
    create = runner.invoke(
        main,
        ["task", "create", "--session", "cli-task", "--title", "Do work"],
        env=cli_env,
    )
    assert create.exit_code == 0
    task_id = create.output.strip()

    listing = runner.invoke(main, ["task", "list", "--session", "cli-task"], env=cli_env)
    assert listing.exit_code == 0
    assert "Do work" in listing.output

    claim = runner.invoke(
        main,
        ["task", "claim", "--session", "cli-task", "--id", task_id, "--assignee", "impl-1"],
        env=cli_env,
    )
    assert claim.exit_code == 0

    done = runner.invoke(
        main,
        ["task", "complete", "--session", "cli-task", "--id", task_id],
        env=cli_env,
    )
    assert done.exit_code == 0
    assert "completed" in done.output


def test_task_missing_session(cli_env: dict) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["task", "list", "--session", "no-such-session"],
        env=cli_env,
    )
    assert result.exit_code == 1
    assert "Session not found" in result.output
