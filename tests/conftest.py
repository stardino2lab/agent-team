"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_team.event_log import EventLog
from agent_team.session import Member, SessionStore


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Isolated directory for future session-dir tests."""
    return tmp_path


@pytest.fixture
def sessions_base(tmp_path: Path) -> Path:
    return tmp_path / "agent-team"


@pytest.fixture
def session_store(sessions_base: Path) -> SessionStore:
    return SessionStore(base_dir=sessions_base)


@pytest.fixture
def session_dir(session_store: SessionStore) -> Path:
    session = session_store.create(
        session_id="test-session",
        project_path="c:\\DEV\\test",
        psmux_session="test-session",
        members=[
            Member(
                name="lead",
                role="lead",
                persona=None,
                cli="claude",
                pane_id="%0",
                backend="psmux",
                status="running",
            )
        ],
    )
    return session_store.session_dir(session.session_id)


@pytest.fixture
def event_log() -> EventLog:
    return EventLog()
