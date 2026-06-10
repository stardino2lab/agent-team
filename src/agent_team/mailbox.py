"""Peer messaging between agents."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from agent_team._io import format_ts, parse_since, parse_ts, safe_segment, utc_now
from agent_team.event_log import EventLog


@dataclass
class Message:
    id: str
    from_: str
    to: str
    body: str
    ts: str


def _message_to_dict(message: Message) -> dict:
    return {
        "id": message.id,
        "from": message.from_,
        "to": message.to,
        "body": message.body,
        "ts": message.ts,
    }


def _message_from_dict(data: dict) -> Message:
    return Message(
        id=data["id"],
        from_=data["from"],
        to=data["to"],
        body=data["body"],
        ts=data["ts"],
    )


def send(
    session_dir: Path,
    *,
    from_: str,
    to: str,
    body: str,
    event_log: EventLog | None = None,
) -> Message:
    safe_segment(to, "recipient")
    message = Message(
        id=str(uuid.uuid4()),
        from_=from_,
        to=to,
        body=body,
        ts=format_ts(utc_now()),
    )
    inbox = session_dir / "mailbox" / f"{to}.jsonl"
    inbox.parent.mkdir(parents=True, exist_ok=True)
    with inbox.open("a", encoding="utf-8") as f:
        f.write(json.dumps(_message_to_dict(message)) + "\n")

    if event_log is not None:
        event_log.append(
            session_dir,
            type_="mail_sent",
            payload={"from": from_, "to": to, "id": message.id},
        )
    return message


def read_inbox(
    session_dir: Path,
    recipient: str,
    since: datetime | str | None = None,
) -> list[Message]:
    safe_segment(recipient, "recipient")
    inbox = session_dir / "mailbox" / f"{recipient}.jsonl"
    if not inbox.exists():
        return []

    since_dt = parse_since(since)
    messages: list[Message] = []
    for line in inbox.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        message = _message_from_dict(json.loads(line))
        if since_dt is not None and parse_ts(message.ts) <= since_dt:
            continue
        messages.append(message)
    return messages
