"""Shared CLI helpers."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import NoReturn

from agent_team._io import InvalidPathSegmentError, safe_segment
from agent_team.personas import PersonaLoadError, PersonaNotFoundError
from agent_team.project_loader import (
    PlaybookLoadError,
    PlaybookNotFoundError,
    ProjectConfigError,
    TeamMdNotFoundError,
)
from agent_team.session import SessionNotFoundError, SessionStore, default_base_dir
from agent_team.tasks import TaskDependencyError, TaskNotFoundError, TaskStateError


class CliError(Exception):
    """CLI usage or session error."""


CLI_ERRORS: tuple[type[Exception], ...] = (
    CliError,
    InvalidPathSegmentError,
    SessionNotFoundError,
    TaskNotFoundError,
    TaskDependencyError,
    TaskStateError,
    PersonaNotFoundError,
    PersonaLoadError,
    ProjectConfigError,
    TeamMdNotFoundError,
    PlaybookNotFoundError,
    PlaybookLoadError,
    ValueError,
)


def resolve_base_dir() -> Path:
    return default_base_dir()


def resolve_session_dir(session_id: str) -> Path:
    store = SessionStore(base_dir=resolve_base_dir())
    session_dir = store.session_dir(session_id)
    if not (session_dir / "session.json").exists():
        raise CliError(f"Session not found: {session_id}")
    return session_dir


def mail_cursor_path(session_dir: Path, recipient: str) -> Path:
    safe_segment(recipient, "recipient")
    return session_dir / ".cli" / f"mail-cursor-{recipient}.json"


def load_mail_cursor(session_dir: Path, recipient: str) -> dict | None:
    path = mail_cursor_path(session_dir, recipient)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CliError(f"Invalid mail cursor file: {path}") from exc
    if not isinstance(data, dict):
        raise CliError(f"Invalid mail cursor file: {path}")
    if not data.get("ts") and not data.get("last_id"):
        return None
    return data


def save_mail_cursor(
    session_dir: Path,
    recipient: str,
    *,
    ts: str,
    last_id: str,
) -> None:
    path = mail_cursor_path(session_dir, recipient)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"ts": ts, "last_id": last_id}) + "\n",
        encoding="utf-8",
    )


def resolve_mail_since(
    session_dir: Path,
    recipient: str,
    since: str | None,
) -> datetime | str | None:
    if since is None or since == "last":
        return None
    return since


def read_mail_messages(session_dir: Path, recipient: str, since: str | None):
    from agent_team.mailbox import read_inbox

    if since == "last":
        cursor = load_mail_cursor(session_dir, recipient)
        return filter_messages_after_cursor(
            read_inbox(session_dir, recipient),
            cursor,
        )
    resolved_since = resolve_mail_since(session_dir, recipient, since)
    return read_inbox(session_dir, recipient, since=resolved_since)


def filter_messages_after_cursor(messages, cursor: dict | None):
    if cursor is None:
        return messages
    last_id = cursor.get("last_id")
    if last_id:
        for index, message in enumerate(messages):
            if message.id == last_id:
                return messages[index + 1 :]
    ts = cursor.get("ts")
    if ts:
        from agent_team._io import parse_ts

        since_dt = parse_ts(ts)
        return [message for message in messages if parse_ts(message.ts) > since_dt]
    return messages


def update_mail_cursor_from_messages(session_dir: Path, recipient: str, messages) -> None:
    if not messages:
        return
    last = messages[-1]
    save_mail_cursor(session_dir, recipient, ts=last.ts, last_id=last.id)


def echo_error(msg: str) -> NoReturn:
    click_echo_error(msg)
    sys.exit(1)


def click_echo_error(msg: str) -> None:
    print(msg, file=sys.stderr)


def follow_poll_seconds() -> float:
    return 0.1


def follow_once() -> bool:
    import os

    return os.environ.get("AGENT_TEAM_FOLLOW_ONCE") == "1"


def follow_sleep() -> None:
    time.sleep(follow_poll_seconds())
