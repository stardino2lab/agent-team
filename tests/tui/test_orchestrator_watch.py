"""Orchestrator FileWatcher integration (real watchfiles)."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from agent_team.event_log import EventLog
from agent_team.orchestrator import Orchestrator, OrchestratorContext
from agent_team.personas import PersonaRegistry
from agent_team.psmux_backend import PsmuxBackend
from agent_team.session import SessionStore
from agent_team.spawn_approval import SpawnApproval
from agent_team.teammate_runner import TeammateRunner


@pytest.fixture
def orchestrator_with_watch(
    session_dir: Path,
    session_store: SessionStore,
    psmux_backend: PsmuxBackend,
    persona_registry: PersonaRegistry,
    event_log: EventLog,
) -> Orchestrator:
    psmux_backend.new_session("test-session")
    runner = TeammateRunner(psmux_backend, persona_registry, mock=True)
    approval = SpawnApproval()
    ctx = OrchestratorContext(
        session_id="test-session",
        session_dir=session_dir,
        store=session_store,
        approval=approval,
        runner=runner,
        psmux=psmux_backend,
        event_log=event_log,
    )
    return Orchestrator(ctx)


def test_orchestrator_watches_resolutions_and_spawns(
    orchestrator_with_watch: Orchestrator,
    event_log: EventLog,
) -> None:
    orch = orchestrator_with_watch
    approval = orch.ctx.approval
    session_dir = orch.ctx.session_dir

    spawn_seen = threading.Event()
    original_run_once = orch.run_once

    def wrapped() -> int:
        n = original_run_once()
        if n > 0:
            spawn_seen.set()
        return n

    orch.run_once = wrapped  # type: ignore[method-assign]
    orch.start_watching()
    try:
        import time as _t

        _t.sleep(0.3)  # let watchfiles attach
        req = approval.request_spawn(
            session_dir,
            persona="planner",
            cli="claude",
            prompt="ping",
            requested_by="lead",
            event_log=event_log,
        )
        approval.approve(
            session_dir, req.request_id, decided_by="user", event_log=event_log
        )
        assert spawn_seen.wait(timeout=8.0), "watcher did not trigger spawn within 8s"
    finally:
        orch.stop_watching()

    session = orch.ctx.store.load(orch.ctx.session_id)
    assert any(m.role == "teammate" for m in session.members)
