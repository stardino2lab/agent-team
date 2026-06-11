"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_team.event_log import EventLog
from agent_team.mcp_server import McpContext
from agent_team.personas import PersonaRegistry
from agent_team.psmux_backend import PsmuxBackend
from agent_team.session import Member, SessionStore
from agent_team.spawn_approval import SpawnApproval


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
def psmux_backend() -> PsmuxBackend:
    return PsmuxBackend(mock=True)


@pytest.fixture
def cli_env(sessions_base: Path) -> dict[str, str]:
    return {"AGENT_TEAM_HOME": str(sessions_base)}


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


@pytest.fixture
def mcp_context(
    session_store: SessionStore,
    consumer_project: Path,
    psmux_backend: PsmuxBackend,
    event_log: EventLog,
    empty_global_personas: Path,
) -> McpContext:
    session = session_store.create(
        session_id="mcp-test",
        project_path=str(consumer_project),
        psmux_session="mcp-test",
        max_teammates=5,
        members=[
            Member(
                name="lead",
                role="lead",
                persona=None,
                cli="claude",
                pane_id="%0",
                backend="psmux",
                status="running",
            ),
            Member(
                name="helper-1",
                role="teammate",
                persona="planner",
                cli="claude",
                pane_id="%1",
                backend="psmux",
                status="running",
            ),
        ],
    )
    return McpContext(
        session_id=session.session_id,
        session_dir=session_store.session_dir(session.session_id),
        project_path=consumer_project,
        store=session_store,
        registry=PersonaRegistry(
            project_path=consumer_project,
            global_dir=empty_global_personas,
        ),
        approval=SpawnApproval(),
        psmux=psmux_backend,
        event_log=event_log,
    )
