"""TUI loader unit tests."""

from __future__ import annotations

from pathlib import Path

from agent_team.event_log import Event, EventLog
from agent_team.session import Session
from agent_team.tasks import claim_task, complete_task, create_task
from agent_team.tui.loaders import (
    format_event_summary,
    load_event_rows,
    load_mail_rows,
    load_member_rows,
    load_task_rows,
)


def test_load_mail_rows_merges_mailboxes_newest_first(tui_session_dir: Path) -> None:
    mailbox = tui_session_dir / "mailbox"
    mailbox.mkdir(exist_ok=True)
    (mailbox / "a.jsonl").write_text(
        '{"ts":"2024-01-01T10:00:00Z","from":"lead","to":"a","body":"old"}\n'
        '{"ts":"2024-01-02T10:00:00Z","from":"lead","to":"a","body":"mid"}\n',
        encoding="utf-8",
    )
    (mailbox / "b.jsonl").write_text(
        '{"ts":"2024-01-03T10:00:00Z","from":"helper-1","to":"lead","body":"newest"}\n',
        encoding="utf-8",
    )

    rows = load_mail_rows(tui_session_dir)
    assert len(rows) == 3
    assert rows[0].body == "newest"
    assert rows[1].body == "mid"
    assert rows[2].body == "old"


def test_format_event_summary_known_types() -> None:
    spawn = Event(
        type="spawn_requested",
        ts="2024-01-01T00:00:00Z",
        payload={"request_id": "apr-001", "persona": "planner"},
    )
    mail = Event(
        type="mail_sent",
        ts="2024-01-01T00:00:00Z",
        payload={"from": "lead", "to": "helper-1"},
    )
    claimed = Event(
        type="task_claimed",
        ts="2024-01-01T00:00:00Z",
        payload={"task_id": "task-001", "assignee": "helper-1"},
    )

    assert format_event_summary(spawn) == "spawn_requested apr-001 planner"
    assert format_event_summary(mail) == "mail_sent lead → helper-1"
    assert format_event_summary(claimed) == "task_claimed task-001 helper-1"


def test_load_task_rows_reflects_states(tui_session_dir: Path, event_log: EventLog) -> None:
    pending = create_task(tui_session_dir, title="Pending work")
    active = create_task(tui_session_dir, title="Active work", event_log=event_log)
    claim_task(tui_session_dir, active.id, assignee="helper-1", event_log=event_log)
    done = create_task(tui_session_dir, title="Done work", event_log=event_log)
    claim_task(tui_session_dir, done.id, assignee="helper-1", event_log=event_log)
    complete_task(tui_session_dir, done.id, event_log=event_log)

    rows = {row.task_id: row for row in load_task_rows(tui_session_dir)}
    assert rows[pending.id].state == "pending"
    assert rows[active.id].state == "in_progress"
    assert rows[active.id].assignee == "helper-1"
    assert rows[done.id].state == "completed"


def test_load_member_rows_lead_and_teammate(tui_session: Session) -> None:
    rows = load_member_rows(tui_session)
    assert len(rows) == 2
    assert rows[0].name == "lead"
    assert rows[0].role == "lead"
    assert rows[1].name == "helper-1"
    assert rows[1].role == "teammate"
    assert rows[1].persona == "planner"


def test_load_event_rows_uses_summaries(tui_session_dir: Path, event_log: EventLog) -> None:
    event_log.append(
        tui_session_dir,
        type_="mail_sent",
        payload={"from": "lead", "to": "helper-1"},
    )

    rows = load_event_rows(tui_session_dir)
    assert len(rows) == 1
    assert rows[0].summary == "mail_sent lead → helper-1"


def test_load_mail_rows_skips_malformed_lines(tui_session_dir: Path) -> None:
    mailbox = tui_session_dir / "mailbox"
    mailbox.mkdir(exist_ok=True)
    (mailbox / "a.jsonl").write_text(
        '{"ts":"2024-01-01T10:00:00Z","from":"lead","to":"a","body":"good"}\n'
        "not json at all\n"
        '{"ts":"2024-01-02T10:00:00Z"}\n'  # missing from/to/body — defaults applied
        '{"from":"x","to":"y","body":"no ts"}\n'  # missing ts — skipped
        '{"ts":"2024-01-03T10:00:00Z","from":"lead","to":"a","body":"later"}\n',
        encoding="utf-8",
    )

    rows = load_mail_rows(tui_session_dir)
    # 3 valid rows: "later", "good", and the ts-only row with empty fields
    assert len(rows) == 3
    assert rows[0].body == "later"


def test_format_event_summary_s8_event_types() -> None:
    started = Event(
        type="session_started",
        ts="2026-06-12T00:00:00Z",
        payload={"session_id": "demo", "members": ["lead", "tui"]},
    )
    ready = Event(
        type="teammate_ready",
        ts="2026-06-12T00:00:01Z",
        payload={"name": "helper-1", "persona": "planner", "pane_id": "%2"},
    )
    err = Event(
        type="error",
        ts="2026-06-12T00:00:02Z",
        payload={"kind": "max_teammates_exceeded"},
    )

    assert format_event_summary(started) == "session_started demo"
    assert format_event_summary(ready) == "teammate_ready helper-1 (planner)"
    assert format_event_summary(err) == "error max_teammates_exceeded"


def test_format_event_summary_tolerates_missing_payload_keys() -> None:
    # task_claimed without assignee: should not raise
    broken = Event(
        type="task_claimed",
        ts="2024-01-01T00:00:00Z",
        payload={"task_id": "task-001"},
    )
    assert "task_claimed task-001" in format_event_summary(broken)

    unknown = Event(type="something_new", ts="2024-01-01T00:00:00Z", payload={})
    assert format_event_summary(unknown) == "something_new"
