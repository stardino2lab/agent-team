"""CLI logs command tests."""

from __future__ import annotations

from click.testing import CliRunner

from agent_team.__main__ import main
from agent_team.session import SessionStore


def test_logs_tail_and_export(cli_env: dict, session_store: SessionStore, tmp_path) -> None:
    session_store.create(
        session_id="cli-logs",
        project_path="c:\\DEV\\test",
        psmux_session="cli-logs",
    )
    runner = CliRunner()
    runner.invoke(
        main,
        ["mail", "send", "--session", "cli-logs", "--to", "lead", "--body", "ping"],
        env=cli_env,
    )

    tail = runner.invoke(
        main,
        ["logs", "tail", "--session", "cli-logs", "--lines", "5"],
        env=cli_env,
    )
    assert tail.exit_code == 0
    assert "mail_sent" in tail.output

    dest = tmp_path / "export.jsonl"
    export = runner.invoke(
        main,
        ["logs", "export", "--session", "cli-logs", "--to", str(dest)],
        env=cli_env,
    )
    assert export.exit_code == 0
    assert dest.exists()
    assert "mail_sent" in dest.read_text(encoding="utf-8")


def test_logs_follow_once(cli_env: dict, session_store: SessionStore) -> None:
    session_store.create(
        session_id="cli-follow",
        project_path="c:\\DEV\\test",
        psmux_session="cli-follow",
    )
    runner = CliRunner()
    env = {**cli_env, "AGENT_TEAM_FOLLOW_ONCE": "1"}
    runner.invoke(
        main,
        ["mail", "send", "--session", "cli-follow", "--to", "lead", "--body", "x"],
        env=env,
    )
    follow = runner.invoke(
        main,
        ["logs", "tail", "--session", "cli-follow", "--follow"],
        env=env,
    )
    assert follow.exit_code == 0
    assert "mail_sent" in follow.output
