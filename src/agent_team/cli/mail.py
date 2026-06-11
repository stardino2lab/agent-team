"""Mail CLI commands."""

from __future__ import annotations

import click

from agent_team.cli._helpers import (
    CLI_ERRORS,
    echo_error,
    read_mail_messages,
    resolve_session_dir,
    update_mail_cursor_from_messages,
)
from agent_team.event_log import EventLog
from agent_team.mailbox import send


@click.group("mail")
def mail_group() -> None:
    """Send and read mailbox messages."""


@mail_group.command("send")
@click.option("--session", required=True, help="Session ID")
@click.option("--to", required=True, help="Recipient name")
@click.option("--body", required=True, help="Message body")
@click.option("--as", "as_name", default="lead", help="Sender identity")
def send_cmd(session: str, to: str, body: str, as_name: str) -> None:
    """Send a message to a teammate inbox."""
    try:
        session_dir = resolve_session_dir(session)
        message = send(
            session_dir,
            from_=as_name,
            to=to,
            body=body,
            event_log=EventLog(),
        )
        click.echo(message.id)
    except CLI_ERRORS as exc:
        echo_error(str(exc))


@mail_group.command("read")
@click.option("--session", required=True, help="Session ID")
@click.option("--as", "as_name", default="lead", help="Inbox recipient")
@click.option("--since", default=None, help="last or ISO8601 timestamp")
def read_cmd(session: str, as_name: str, since: str | None) -> None:
    """Read messages from an inbox."""
    try:
        session_dir = resolve_session_dir(session)
        messages = read_mail_messages(session_dir, as_name, since)
        for message in messages:
            click.echo(f"{message.ts} {message.from_} -> {message.to}: {message.body}")
        update_mail_cursor_from_messages(session_dir, as_name, messages)
    except CLI_ERRORS as exc:
        echo_error(str(exc))
