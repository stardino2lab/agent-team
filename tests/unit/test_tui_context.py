"""TUI context resolution tests."""

from __future__ import annotations

import pytest

from agent_team.event_log import EventLog
from agent_team.session import Session, SessionStore
from agent_team.tui.context import resolve_tui_context


def test_resolve_from_agent_team_session_id_env(
    tui_session: Session,
    session_store: SessionStore,
    event_log: EventLog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_TEAM_HOME", str(session_store.base_dir))
    monkeypatch.setenv("AGENT_TEAM_SESSION_ID", tui_session.session_id)

    ctx = resolve_tui_context(store=session_store, event_log=event_log)
    assert ctx.session_id == "tui-test"
    assert ctx.session_dir.name == "tui-test"
