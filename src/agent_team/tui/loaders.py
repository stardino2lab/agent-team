"""Pure data loaders for TUI panels."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agent_team import tasks
from agent_team._io import parse_ts
from agent_team.event_log import Event, EventLog
from agent_team.session import Session


@dataclass
class MailRow:
    ts: str
    from_: str
    to: str
    body: str


@dataclass
class TaskRow:
    task_id: str
    title: str
    state: str
    assignee: str | None


@dataclass
class MemberRow:
    name: str
    role: str
    persona: str | None
    cli: str
    pane_id: str | None
    status: str


@dataclass
class EventRow:
    ts: str
    type: str
    summary: str


def load_mail_rows(session_dir: Path, *, limit: int = 100) -> list[MailRow]:
    mailbox_dir = session_dir / "mailbox"
    if not mailbox_dir.exists():
        return []

    rows: list[MailRow] = []
    for inbox in mailbox_dir.glob("*.jsonl"):
        for line in inbox.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = data.get("ts")
            if not isinstance(ts, str):
                continue
            rows.append(
                MailRow(
                    ts=ts,
                    from_=str(data.get("from", "")),
                    to=str(data.get("to", "")),
                    body=str(data.get("body", "")),
                )
            )

    rows.sort(key=lambda r: parse_ts(r.ts), reverse=True)
    return rows[:limit]


def load_task_rows(session_dir: Path) -> list[TaskRow]:
    return [
        TaskRow(
            task_id=task.id,
            title=task.title,
            state=task.state,
            assignee=task.assignee,
        )
        for task in sorted(tasks.list_tasks(session_dir), key=lambda t: t.id)
    ]


def load_member_rows(session: Session) -> list[MemberRow]:
    return [
        MemberRow(
            name=member.name,
            role=member.role,
            persona=member.persona,
            cli=member.cli,
            pane_id=member.pane_id,
            status=member.status,
        )
        for member in session.members
    ]


def format_event_summary(event: Event) -> str:
    p = event.payload
    match event.type:
        case "spawn_requested":
            return f"spawn_requested {p.get('request_id', '')} {p.get('persona', '')}".strip()
        case "mail_sent":
            return f"mail_sent {p.get('from', '')} → {p.get('to', '')}"
        case "task_claimed":
            return f"task_claimed {p.get('task_id', '')} {p.get('assignee', '')}"
        case "task_created":
            return f"task_created {p.get('task_id', '')} {p.get('title', '')}"
        case "task_completed":
            return f"task_completed {p.get('task_id', '')}"
        case "spawn_approved":
            return f"spawn_approved {p.get('request_id', '')} {p.get('persona', '')}"
        case "spawn_denied":
            return f"spawn_denied {p.get('request_id', '')}"
        case "teammate_shutdown":
            return f"teammate_shutdown {p.get('name', '')}"
        case "session_started":
            return f"session_started {p.get('session_id', '')}"
        case "orchestrator_stopped":
            return f"orchestrator_stopped {p.get('session_id', '')}".strip()
        case "teammate_ready":
            return (
                f"teammate_ready {p.get('name', '')} "
                f"({p.get('persona', '')})"
            ).strip()
        case "error":
            return f"error {p.get('kind', '')}".strip()
        case _:
            return event.type


def load_event_rows(session_dir: Path, *, n: int = 50) -> list[EventRow]:
    log = EventLog()
    return [
        EventRow(ts=event.ts, type=event.type, summary=format_event_summary(event))
        for event in log.tail(session_dir, n=n)
    ]
