"""Orchestrator spawn retry/recovery (S14b)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from agent_team import recovery
from agent_team._io import utc_now
from agent_team.event_log import EventLog
from agent_team.orchestrator import Orchestrator, OrchestratorContext
from agent_team.personas import PersonaRegistry
from agent_team.psmux_backend import PsmuxBackend
from agent_team.session import SessionStore
from agent_team.spawn_approval import SpawnApproval
from agent_team.terminal_backend import BackendCommandError


class _Runner:
    """Stub teammate runner: raises BackendCommandError for the first N spawns."""

    def __init__(self, fail_times: int) -> None:
        self.fail_times = fail_times
        self.calls = 0

    def spawn(self, **kw):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise BackendCommandError(
                "split-window failed", exit_code=1, command_args=["split-window"], stderr="x"
            )
        return SimpleNamespace(pane_id="%5")


def _build(session_dir, session_store, psmux_backend, persona_registry, event_log, runner):
    ctx = OrchestratorContext(
        session_id="test-session",
        session_dir=session_dir,
        store=session_store,
        approval=SpawnApproval(),
        runner=runner,
        psmux=psmux_backend,
        event_log=event_log,
    )
    orch = Orchestrator(ctx)
    # Disable the real background timer; tests drive _retry_sweep directly.
    orch._arm_retry_timer = lambda: None  # type: ignore[method-assign]
    return orch, ctx


def _approve(approval, session_dir, event_log) -> str:
    req = approval.request_spawn(
        session_dir, persona="planner", cli="claude", prompt="go",
        requested_by="lead", event_log=event_log,
    )
    approval.approve(session_dir, req.request_id, decided_by="user", event_log=event_log)
    return req.request_id


def test_spawn_failure_records_retry(
    session_dir: Path, session_store: SessionStore, psmux_backend: PsmuxBackend,
    persona_registry: PersonaRegistry, event_log: EventLog,
) -> None:
    runner = _Runner(fail_times=99)
    orch, ctx = _build(
        session_dir, session_store, psmux_backend, persona_registry, event_log, runner
    )
    rid = _approve(ctx.approval, session_dir, event_log)

    orch.run_once()  # spawn raises -> retry recorded, no member created

    retries = recovery.read_retries(session_dir)
    assert rid in retries and retries[rid].attempts == 1
    members = session_store.load("test-session").members
    assert all(m.role != "teammate" for m in members)
    events = [e.type for e in event_log.read(session_dir)]
    assert "spawn_retry_scheduled" in events


def test_retry_sweep_reattempts_and_succeeds(
    session_dir: Path, session_store: SessionStore, psmux_backend: PsmuxBackend,
    persona_registry: PersonaRegistry, event_log: EventLog,
) -> None:
    runner = _Runner(fail_times=1)  # first spawn fails, second succeeds
    orch, ctx = _build(
        session_dir, session_store, psmux_backend, persona_registry, event_log, runner
    )
    rid = _approve(ctx.approval, session_dir, event_log)

    orch.run_once()  # fails -> retry recorded
    # Make the retry eligible now, then sweep.
    recovery.record_retry(
        session_dir, request_id=rid, attempts=1,
        next_eligible=utc_now() - timedelta(seconds=1), last_error="x",
    )
    orch._retry_sweep()

    members = session_store.load("test-session").members
    assert any(m.role == "teammate" and m.pane_id == "%5" for m in members)
    assert rid not in recovery.read_retries(session_dir)  # cleared on success


def test_retries_exhaust_to_terminal_error(
    session_dir: Path, session_store: SessionStore, psmux_backend: PsmuxBackend,
    persona_registry: PersonaRegistry, event_log: EventLog,
) -> None:
    runner = _Runner(fail_times=99)
    orch, ctx = _build(
        session_dir, session_store, psmux_backend, persona_registry, event_log, runner
    )
    _approve(ctx.approval, session_dir, event_log)
    res = ctx.approval.read_resolutions(session_dir)[0]

    for _ in range(recovery.MAX_SPAWN_RETRIES):
        orch._spawn_one(res)

    errors = [e for e in event_log.read(session_dir) if e.type == "error"]
    assert any(e.payload.get("kind") == "spawn_failed" for e in errors)
    assert recovery.read_retries(session_dir) == {}  # cleared after exhaustion


def test_hard_stop_does_not_retry(
    session_dir: Path, session_store: SessionStore, psmux_backend: PsmuxBackend,
    persona_registry: PersonaRegistry, event_log: EventLog,
) -> None:
    # An invalid resolution (no persona/cli) is a hard stop — never retried.
    runner = _Runner(fail_times=0)
    orch, ctx = _build(
        session_dir, session_store, psmux_backend, persona_registry, event_log, runner
    )
    from agent_team.spawn_approval import SpawnResolution

    bad = SpawnResolution(
        request_id="apr-x", decision="approved", decided_at="t", decided_by="user",
        persona=None, cli=None,
    )
    assert orch._spawn_one(bad) is False
    assert recovery.read_retries(session_dir) == {}


def test_sweep_drops_orphan_retry_no_busy_loop(
    session_dir: Path, session_store: SessionStore, psmux_backend: PsmuxBackend,
    persona_registry: PersonaRegistry, event_log: EventLog,
) -> None:
    # An eligible retry whose request_id has NO approved resolution must be CLEARED
    # by the sweep, else _arm_retry_timer would re-fire at 0 delay (busy loop).
    runner = _Runner(fail_times=0)
    orch, ctx = _build(
        session_dir, session_store, psmux_backend, persona_registry, event_log, runner
    )
    recovery.record_retry(
        session_dir, request_id="apr-orphan", attempts=1,
        next_eligible=utc_now() - timedelta(seconds=1), last_error="x",
    )
    orch._retry_sweep()
    assert recovery.read_retries(session_dir) == {}
