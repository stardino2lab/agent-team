"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_team.event_log import EventLog
from agent_team.personas import PersonaRegistry
from agent_team.session import Member, SessionStore


@pytest.fixture
def empty_global_personas(tmp_path: Path) -> Path:
    """Isolated global personas dir (missing = skip layer)."""
    return tmp_path / "no-global-personas"


@pytest.fixture
def persona_registry(empty_global_personas: Path) -> PersonaRegistry:
    return PersonaRegistry(global_dir=empty_global_personas)


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


@pytest.fixture
def consumer_project(tmp_path: Path) -> Path:
    """Minimal consumer project after init."""
    from click.testing import CliRunner

    from agent_team.__main__ import main

    project = tmp_path / "payment-api"
    project.mkdir()
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--project", str(project)])
    assert result.exit_code == 0, result.output
    return project
