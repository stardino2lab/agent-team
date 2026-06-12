"""Orchestrator unit tests."""

from __future__ import annotations

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
def orchestrator(
    session_dir: Path,
    session_store: SessionStore,
    psmux_backend: PsmuxBackend,
    persona_registry: PersonaRegistry,
    event_log: EventLog,
) -> Orchestrator:
    psmux_backend.new_session("test-session")
    runner = TeammateRunner(psmux_backend, persona_registry, mock=False)
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


@pytest.fixture
def no_psmux_orchestrator(
    session_dir: Path,
    session_store: SessionStore,
    psmux_backend: PsmuxBackend,
    persona_registry: PersonaRegistry,
    event_log: EventLog,
) -> Orchestrator:
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
        no_psmux=True,
    )
    return Orchestrator(ctx)


def _request_and_approve(
    *,
    approval: SpawnApproval,
    session_dir: Path,
    event_log: EventLog,
    persona: str = "planner",
    prompt: str = "Plan it.",
    teammate_name: str | None = None,
) -> str:
    req = approval.request_spawn(
        session_dir,
        persona=persona,
        cli="claude",
        prompt=prompt,
        requested_by="lead",
        teammate_name=teammate_name,
        event_log=event_log,
    )
    approval.approve(
        session_dir,
        req.request_id,
        decided_by="user",
        event_log=event_log,
    )
    return req.request_id


def test_run_once_spawns_for_approved(
    orchestrator: Orchestrator,
    event_log: EventLog,
) -> None:
    _request_and_approve(
        approval=orchestrator.ctx.approval,
        session_dir=orchestrator.ctx.session_dir,
        event_log=event_log,
    )
    n = orchestrator.run_once()
    assert n == 1
    assert len(orchestrator.ctx.runner.recorded_spawns) == 1


def test_run_once_emits_teammate_ready(
    orchestrator: Orchestrator,
    event_log: EventLog,
) -> None:
    _request_and_approve(
        approval=orchestrator.ctx.approval,
        session_dir=orchestrator.ctx.session_dir,
        event_log=event_log,
        persona="planner",
    )
    orchestrator.run_once()
    events = [e for e in event_log.read(orchestrator.ctx.session_dir) if e.type == "teammate_ready"]
    assert len(events) == 1
    p = events[0].payload
    assert p["persona"] == "planner"
    assert p["name"].startswith("helper-")
    assert p["pane_id"].startswith("%")
    assert p["cli"] == "claude"
    assert p["request_id"].startswith("apr-")


def test_run_once_updates_member_status(
    orchestrator: Orchestrator,
    event_log: EventLog,
) -> None:
    _request_and_approve(
        approval=orchestrator.ctx.approval,
        session_dir=orchestrator.ctx.session_dir,
        event_log=event_log,
    )
    orchestrator.run_once()
    session = orchestrator.ctx.store.load(orchestrator.ctx.session_id)
    teammates = [m for m in session.members if m.role == "teammate"]
    assert len(teammates) == 1
    t = teammates[0]
    assert t.status == "running"
    assert t.pane_id is not None
    assert t.persona == "planner"
    assert t.name == "helper-1"


def test_run_once_idempotent_on_handled(
    orchestrator: Orchestrator,
    event_log: EventLog,
) -> None:
    _request_and_approve(
        approval=orchestrator.ctx.approval,
        session_dir=orchestrator.ctx.session_dir,
        event_log=event_log,
    )
    assert orchestrator.run_once() == 1
    assert orchestrator.run_once() == 0
    assert len(orchestrator.ctx.runner.recorded_spawns) == 1


def test_run_once_skips_denied(
    orchestrator: Orchestrator,
    event_log: EventLog,
) -> None:
    approval = orchestrator.ctx.approval
    session_dir = orchestrator.ctx.session_dir
    req = approval.request_spawn(
        session_dir,
        persona="planner",
        cli="claude",
        prompt="x",
        requested_by="lead",
        event_log=event_log,
    )
    approval.deny(session_dir, req.request_id, decided_by="user", event_log=event_log)
    assert orchestrator.run_once() == 0


def test_no_psmux_skips_pane_split(
    no_psmux_orchestrator: Orchestrator,
    event_log: EventLog,
) -> None:
    _request_and_approve(
        approval=no_psmux_orchestrator.ctx.approval,
        session_dir=no_psmux_orchestrator.ctx.session_dir,
        event_log=event_log,
    )
    no_psmux_orchestrator.run_once()

    calls = no_psmux_orchestrator.ctx.psmux.recorded_calls
    assert not any("split-window" in c.args for c in calls)
    session = no_psmux_orchestrator.ctx.store.load(no_psmux_orchestrator.ctx.session_id)
    teammates = [m for m in session.members if m.role == "teammate"]
    # pane_id is None for no_psmux members so it doesn't masquerade as a
    # real psmux pane id (which must match `%[0-9]+`).
    assert teammates and teammates[0].pane_id is None


def test_run_once_caps_at_max_teammates(
    orchestrator: Orchestrator,
    event_log: EventLog,
    session_store: SessionStore,
) -> None:
    session = session_store.load(orchestrator.ctx.session_id)
    session.max_teammates = 1
    session_store.save(session)

    _request_and_approve(
        approval=orchestrator.ctx.approval,
        session_dir=orchestrator.ctx.session_dir,
        event_log=event_log,
        teammate_name="helper-1",
    )
    assert orchestrator.run_once() == 1

    _request_and_approve(
        approval=orchestrator.ctx.approval,
        session_dir=orchestrator.ctx.session_dir,
        event_log=event_log,
        teammate_name="helper-2",
    )
    assert orchestrator.run_once() == 0
    errors = [e for e in event_log.read(orchestrator.ctx.session_dir) if e.type == "error"]
    cap_err = next(
        e for e in errors if e.payload.get("kind") == "max_teammates_exceeded"
    )
    assert cap_err.payload["existing_teammates"] == ["helper-1"]
    assert cap_err.payload["max_teammates"] == 1


def test_start_cleans_up_session_dir_on_partial_failure(
    consumer_project: Path,
    session_store: SessionStore,
    psmux_backend: PsmuxBackend,
    persona_registry: PersonaRegistry,
    event_log: EventLog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = TeammateRunner(psmux_backend, persona_registry, mock=True)
    ctx = OrchestratorContext(
        session_id="cleanup-me",
        session_dir=session_store.session_dir("cleanup-me"),
        store=session_store,
        approval=SpawnApproval(),
        runner=runner,
        psmux=psmux_backend,
        event_log=event_log,
        no_psmux=False,
    )
    orch = Orchestrator(ctx)

    def boom(*_a, **_kw):  # type: ignore[no-untyped-def]
        raise RuntimeError("psmux exploded")

    monkeypatch.setattr(psmux_backend, "new_session", boom)

    with pytest.raises(RuntimeError):
        orch.start(project_path=consumer_project)

    assert not ctx.session_dir.exists(), (
        "session_dir must be wiped so a subsequent `start` with the same id works"
    )


def test_attach_method_is_idempotent_across_restarts(
    orchestrator: Orchestrator,
    event_log: EventLog,
) -> None:
    _request_and_approve(
        approval=orchestrator.ctx.approval,
        session_dir=orchestrator.ctx.session_dir,
        event_log=event_log,
        teammate_name=None,
    )
    assert orchestrator.run_once() == 1

    fresh = Orchestrator(orchestrator.ctx)
    try:
        fresh.attach()
    finally:
        fresh.stop_watching()

    session = orchestrator.ctx.store.load(orchestrator.ctx.session_id)
    teammates = [m for m in session.members if m.role == "teammate"]
    assert len(teammates) == 1, "attach must not re-spawn already-handled work"


def test_start_creates_session_and_session_started_event(
    consumer_project: Path,
    session_store: SessionStore,
    psmux_backend: PsmuxBackend,
    persona_registry: PersonaRegistry,
    event_log: EventLog,
) -> None:
    runner = TeammateRunner(psmux_backend, persona_registry, mock=True)
    ctx = OrchestratorContext(
        session_id="start-unit",
        session_dir=session_store.session_dir("start-unit"),
        store=session_store,
        approval=SpawnApproval(),
        runner=runner,
        psmux=psmux_backend,
        event_log=event_log,
        no_psmux=False,
    )
    orch = Orchestrator(ctx)
    try:
        session = orch.start(project_path=consumer_project)
    finally:
        orch.stop_watching()

    assert session.session_id == "start-unit"
    assert any(m.name == "lead" for m in session.members)
    lead = next(m for m in session.members if m.name == "lead")
    assert lead.status == "running"
    assert lead.pane_id is not None

    events = event_log.read(ctx.session_dir)
    started = [e for e in events if e.type == "session_started"]
    assert len(started) == 1
    p = started[0].payload
    assert "lead" in p["members"]
    assert "tui" in p["members"]
    assert p["session_id"] == "start-unit"

    split_calls = [c for c in psmux_backend.recorded_calls if "split-window" in c.args]
    assert any("python -m agent_team.tui" in " ".join(c.args) for c in split_calls)


def test_run_once_skips_malformed_resolution_line(
    orchestrator: Orchestrator,
    event_log: EventLog,
) -> None:
    approval_dir = orchestrator.ctx.session_dir / "approval"
    approval_dir.mkdir(parents=True, exist_ok=True)
    resolutions = approval_dir / "resolutions.jsonl"
    resolutions.write_text(
        "not valid json\n"
        '{"request_id":"apr-001","decision":"approved",'
        '"decided_at":"2026-06-12T00:00:00Z","decided_by":"user",'
        '"persona":"planner","cli":"claude","prompt":"x"}\n',
        encoding="utf-8",
    )
    assert orchestrator.run_once() == 1


def test_run_once_emits_error_on_invalid_resolution_payload(
    orchestrator: Orchestrator,
    event_log: EventLog,
) -> None:
    approval_dir = orchestrator.ctx.session_dir / "approval"
    approval_dir.mkdir(parents=True, exist_ok=True)
    (approval_dir / "resolutions.jsonl").write_text(
        '{"request_id":"apr-001","decision":"approved",'
        '"decided_at":"2026-06-12T00:00:00Z","decided_by":"user"}\n',  # persona/cli missing
        encoding="utf-8",
    )
    assert orchestrator.run_once() == 0
    errs = [e for e in event_log.read(orchestrator.ctx.session_dir) if e.type == "error"]
    assert any(e.payload.get("kind") == "invalid_resolution" for e in errs)


def test_reconcile_handled_uses_teammate_ready_events_when_name_absent(
    orchestrator: Orchestrator,
    event_log: EventLog,
) -> None:
    # request without teammate_name (the realistic MCP / Python API case)
    _request_and_approve(
        approval=orchestrator.ctx.approval,
        session_dir=orchestrator.ctx.session_dir,
        event_log=event_log,
        teammate_name=None,
    )
    assert orchestrator.run_once() == 1

    # New orchestrator simulating attach
    fresh = Orchestrator(orchestrator.ctx)
    fresh.reconcile_handled()
    assert fresh.run_once() == 0, (
        "attach must not re-spawn an already-handled resolution"
    )


def test_reconcile_handled_skips_existing_teammates(
    orchestrator: Orchestrator,
    event_log: EventLog,
) -> None:
    _request_and_approve(
        approval=orchestrator.ctx.approval,
        session_dir=orchestrator.ctx.session_dir,
        event_log=event_log,
        teammate_name="helper-1",
    )
    # First orchestrator handles it
    orchestrator.run_once()

    # New orchestrator simulating attach
    fresh = Orchestrator(orchestrator.ctx)
    fresh.reconcile_handled()
    assert fresh.run_once() == 0
