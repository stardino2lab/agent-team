"""Mailbox unit tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from agent_team._io import InvalidPathSegmentError
from agent_team.event_log import EventLog
from agent_team.mailbox import read_inbox, send


def test_send_appends_to_recipient_inbox(session_dir: Path) -> None:
    message = send(session_dir, from_="lead", to="planner-1", body="Hello")

    inbox = session_dir / "mailbox" / "planner-1.jsonl"
    assert inbox.exists()
    assert message.id in inbox.read_text(encoding="utf-8")
    assert '"from": "lead"' in inbox.read_text(encoding="utf-8")


def test_read_inbox_all_messages(session_dir: Path) -> None:
    send(session_dir, from_="lead", to="lead", body="one")
    send(session_dir, from_="planner-1", to="lead", body="two")

    messages = read_inbox(session_dir, "lead")
    assert len(messages) == 2
    assert messages[0].body == "one"
    assert messages[1].body == "two"


def test_read_inbox_since_filter(session_dir: Path) -> None:
    send(session_dir, from_="lead", to="lead", body="first")
    send(session_dir, from_="lead", to="lead", body="second")
    messages = read_inbox(session_dir, "lead")

    early = datetime.fromisoformat(messages[0].ts.replace("Z", "+00:00")) - timedelta(seconds=10)
    assert len(read_inbox(session_dir, "lead", since=early)) == 2

    late = datetime.fromisoformat(messages[1].ts.replace("Z", "+00:00")) + timedelta(seconds=10)
    assert read_inbox(session_dir, "lead", since=late) == []


def test_read_inbox_missing_returns_empty(session_dir: Path) -> None:
    assert read_inbox(session_dir, "nobody") == []


def test_read_inbox_since_iso_string(session_dir: Path) -> None:
    send(session_dir, from_="lead", to="lead", body="only")
    assert read_inbox(session_dir, "lead", since="2099-01-01T00:00:00Z") == []


def test_send_without_event_log(session_dir: Path) -> None:
    send(session_dir, from_="lead", to="lead", body="quiet")
    assert not (session_dir / "events.jsonl").exists()


def test_invalid_recipient_rejected(session_dir: Path) -> None:
    with pytest.raises(InvalidPathSegmentError):
        send(session_dir, from_="lead", to="../evil", body="x")


def test_send_records_mail_sent_event(session_dir: Path, event_log: EventLog) -> None:
    message = send(
        session_dir,
        from_="lead",
        to="planner-1",
        body="task please",
        event_log=event_log,
    )

    events = event_log.read(session_dir)
    assert len(events) == 1
    assert events[0].type == "mail_sent"
    assert events[0].payload == {"from": "lead", "to": "planner-1", "id": message.id}
