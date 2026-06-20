"""Shared CLI helpers."""

from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import NoReturn

from agent_team._io import InvalidPathSegmentError, safe_segment
from agent_team.event_log import EventLog
from agent_team.orchestrator import Orchestrator, OrchestratorContext
from agent_team.personas import PersonaLoadError, PersonaNotFoundError, PersonaRegistry
from agent_team.project_loader import (
    PlaybookLoadError,
    PlaybookNotFoundError,
    ProjectConfigError,
    TeamMdNotFoundError,
)
from agent_team.session import SessionNotFoundError, SessionStore, default_base_dir
from agent_team.spawn_approval import SpawnApproval, SpawnRequestNotFoundError
from agent_team.tasks import TaskDependencyError, TaskNotFoundError, TaskStateError
from agent_team.teammate_runner import TeammateRunner
from agent_team.terminal_backend import TerminalBackend


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
    # Approving/denying with nothing pending (a LookupError, so not covered by the
    # ValueError catch below). SpawnRequestMismatchError is a ValueError -> already
    # caught; do NOT remove ValueError thinking it's redundant.
    SpawnRequestNotFoundError,
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


def make_orchestrator(
    *,
    session_id: str,
    project_path: Path,
    psmux: TerminalBackend,
    no_psmux: bool,
    dry_run: bool,
) -> Orchestrator:
    """Assemble the standard orchestrator wiring shared by start/attach."""
    store = SessionStore()
    registry = PersonaRegistry(project_path=project_path)
    runner = TeammateRunner(psmux, registry, mock=dry_run)
    ctx = OrchestratorContext(
        session_id=session_id,
        session_dir=store.session_dir(session_id),
        store=store,
        approval=SpawnApproval(),
        runner=runner,
        psmux=psmux,
        event_log=EventLog(),
        no_psmux=no_psmux,
    )
    return Orchestrator(ctx)


# --- graceful stop lifecycle (S18b1) ---------------------------------------

_STOP_POLL_INTERVAL = 0.5


def _stop_marker(session_dir: Path) -> Path:
    return session_dir / "control" / "stop"


def stop_requested(session_dir: Path) -> bool:
    """True if a graceful `agent-team stop` has been requested for this session."""
    return _stop_marker(session_dir).exists()


def request_stop(session_dir: Path) -> None:
    """Raise the stop marker the running orchestrator's watch loop polls for."""
    marker = _stop_marker(session_dir)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("", encoding="utf-8")


def clear_stop(session_dir: Path) -> None:
    """Drop a stale stop marker at start/attach time so a prior `stop` can't make
    this fresh run exit instantly. Cleared on STARTUP (not in the loop or in
    `stop`) so a stop issued DURING this run still registers."""
    _stop_marker(session_dir).unlink(missing_ok=True)


def block_until_stopped(
    orch: Orchestrator,
    session_id: str,
    *,
    no_block: bool,
    manifest: bool = False,
) -> None:
    """Block the foreground run until Ctrl-C or a graceful `stop` marker.

    The supported "start and walk away" mode: Hermes backgrounds the process and
    later runs `agent-team stop`, which records the terminal orchestrator_stopped
    event and raises the marker this loop polls. On a marker stop we do NOT
    re-emit (stop already recorded it, BEFORE the marker, so the manifest sees it);
    Ctrl-C / fall-through emits `orchestrator_stopped{reason:"user"}` here.
    """
    from agent_team.manifest import write_manifest_cache

    session_dir = orch.ctx.session_dir
    try:
        if no_block:
            return
        stop_event = threading.Event()
        try:
            while not stop_event.wait(timeout=_STOP_POLL_INTERVAL):
                if stop_requested(session_dir):
                    break
        except KeyboardInterrupt:
            pass
    finally:
        orch.stop_watching()
        if not stop_requested(session_dir):
            orch.ctx.event_log.append(
                session_dir,
                type_="orchestrator_stopped",
                payload={"session_id": session_id, "reason": "user"},
            )
        # S16b: best-effort manifest cache for the graceful-exit fast read. Skipped
        # on --no-block (a test detach, not a real stop). A crash skips it and
        # Hermes regenerates via `logs manifest`.
        if manifest and not no_block:
            try:
                write_manifest_cache(orch.ctx.store.load(session_id), session_dir)
            except Exception:
                pass
