"""CLI mail command tests."""

from __future__ import annotations

from click.testing import CliRunner

from agent_team.__main__ import main
from agent_team.cli._helpers import load_mail_cursor
from agent_team.session import SessionStore


def test_mail_send_and_read(cli_env: dict, session_store: SessionStore) -> None:
    session_store.create(
        session_id="cli-mail",
        project_path="c:\\DEV\\test",
        psmux_session="cli-mail",
    )
    runner = CliRunner()
    send = runner.invoke(
        main,
        ["mail", "send", "--session", "cli-mail", "--to", "lead", "--body", "hello"],
        env=cli_env,
    )
    assert send.exit_code == 0, send.output

    read = runner.invoke(
        main,
        ["mail", "read", "--session", "cli-mail", "--as", "lead"],
        env=cli_env,
    )
    assert read.exit_code == 0
    assert "hello" in read.output


def test_mail_since_last(cli_env: dict, session_store: SessionStore) -> None:
    session_store.create(
        session_id="cli-since",
        project_path="c:\\DEV\\test",
        psmux_session="cli-since",
    )
    runner = CliRunner()
    runner.invoke(
        main,
        ["mail", "send", "--session", "cli-since", "--to", "lead", "--body", "first"],
        env=cli_env,
    )
    runner.invoke(
        main,
        ["mail", "read", "--session", "cli-since", "--as", "lead"],
        env=cli_env,
    )
    runner.invoke(
        main,
        ["mail", "send", "--session", "cli-since", "--to", "lead", "--body", "second"],
        env=cli_env,
    )
    read = runner.invoke(
        main,
        ["mail", "read", "--session", "cli-since", "--as", "lead", "--since", "last"],
        env=cli_env,
    )
    assert read.exit_code == 0
    assert "second" in read.output
    assert "first" not in read.output

    session_dir = session_store.session_dir("cli-since")
    cursor = load_mail_cursor(session_dir, "lead")
    assert cursor is not None
    assert cursor.get("last_id")


def test_mail_invalid_session(cli_env: dict) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["mail", "send", "--session", "../evil", "--to", "lead", "--body", "x"],
        env=cli_env,
    )
    assert result.exit_code == 1


def test_mail_malformed_cursor(cli_env: dict, session_store: SessionStore) -> None:
    session_store.create(
        session_id="cli-cursor",
        project_path="c:\\DEV\\test",
        psmux_session="cli-cursor",
    )
    session_dir = session_store.session_dir("cli-cursor")
    cursor_path = session_dir / ".cli" / "mail-cursor-lead.json"
    cursor_path.parent.mkdir(parents=True, exist_ok=True)
    cursor_path.write_text("not-json", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["mail", "read", "--session", "cli-cursor", "--as", "lead", "--since", "last"],
        env=cli_env,
    )
    assert result.exit_code == 1
    assert "Invalid mail cursor" in result.output
