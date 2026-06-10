"""Append-only audit event log."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from agent_team._io import format_ts, parse_since, parse_ts, utc_now


@dataclass
class Event:
    type: str
    ts: str
    payload: dict


class EventLog:
    def _path(self, session_dir: Path) -> Path:
        return session_dir / "events.jsonl"

    def append(
        self,
        session_dir: Path,
        *,
        type_: str,
        payload: dict,
        ts: datetime | None = None,
    ) -> Event:
        event = Event(type=type_, ts=format_ts(ts or utc_now()), payload=payload)
        line = json.dumps({"type": event.type, "ts": event.ts, "payload": event.payload})
        path = self._path(session_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        return event

    def read(
        self,
        session_dir: Path,
        since: datetime | str | None = None,
    ) -> list[Event]:
        path = self._path(session_dir)
        if not path.exists():
            return []

        since_dt = parse_since(since)
        events: list[Event] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            event = Event(type=data["type"], ts=data["ts"], payload=data["payload"])
            if since_dt is not None and parse_ts(event.ts) <= since_dt:
                continue
            events.append(event)
        return events

    def tail(self, session_dir: Path, n: int = 50) -> list[Event]:
        events = self.read(session_dir)
        return events[-n:]
