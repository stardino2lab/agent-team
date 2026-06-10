"""EventLog unit tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from agent_team.event_log import EventLog


def test_append_multiple_events(session_dir: Path, event_log: EventLog) -> None:
    event_log.append(session_dir, type_="session_started", payload={"session_id": "x"})
    event_log.append(session_dir, type_="mail_sent", payload={"from": "lead", "to": "a", "id": "1"})

    events = event_log.read(session_dir)
    assert len(events) == 2
    assert events[0].type == "session_started"
    assert events[1].type == "mail_sent"


def test_read_since_and_tail(session_dir: Path, event_log: EventLog) -> None:
    t0 = datetime.fromisoformat("2026-06-10T12:00:00+00:00")
    event_log.append(
        session_dir, type_="task_created", payload={"task_id": "task-001"}, ts=t0
    )
    event_log.append(
        session_dir,
        type_="task_claimed",
        payload={"task_id": "task-001"},
        ts=t0 + timedelta(seconds=1),
    )
    event_log.append(
        session_dir,
        type_="task_completed",
        payload={"task_id": "task-001"},
        ts=t0 + timedelta(seconds=2),
    )

    filtered = event_log.read(session_dir, since=t0)
    assert len(filtered) == 2
    assert filtered[0].type == "task_claimed"

    tail = event_log.tail(session_dir, n=2)
    assert len(tail) == 2
    assert tail[-1].type == "task_completed"
