"""TUI session context."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from agent_team.event_log import EventLog
from agent_team.session import SessionStore
from agent_team.spawn_approval import SpawnApproval


class TuiConfigError(RuntimeError):
    """Raised when required TUI configuration is missing."""


@dataclass
class TuiContext:
    session_id: str
    session_dir: Path
    store: SessionStore
    approval: SpawnApproval
    event_log: EventLog


def resolve_tui_context(
    *,
    session_id: str | None = None,
    store: SessionStore | None = None,
    approval: SpawnApproval | None = None,
    event_log: EventLog | None = None,
) -> TuiContext:
    sid = session_id or os.environ.get("AGENT_TEAM_SESSION_ID")
    if not sid:
        raise TuiConfigError("Session id required: --session or AGENT_TEAM_SESSION_ID")

    session_store = store or SessionStore()
    session_store.load(sid)
    return TuiContext(
        session_id=sid,
        session_dir=session_store.session_dir(sid),
        store=session_store,
        approval=approval or SpawnApproval(),
        event_log=event_log or EventLog(),
    )
