"""S18b1: graceful `stop` command + block_until_stopped lifecycle."""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from agent_team.__main__ import main
from agent_team.cli._helpers import (
    _install_sigterm,
    block_until_stopped,
    clear_stop,
    request_stop,
    stop_requested,
)
from agent_team.event_log import EventLog
from agent_team.session import SessionStore

# --- marker helpers ---------------------------------------------------------


def test_stop_marker_roundtrip(tmp_path: Path) -> None:
    assert stop_requested(tmp_path) is False
    request_stop(tmp_path)
    assert stop_requested(tmp_path) is True
    clear_stop(tmp_path)
    assert stop_requested(tmp_path) is False
    clear_stop(tmp_path)  # idempotent: clearing an absent marker is a no-op


# --- block_until_stopped emit logic (no threading needed) -------------------


def _fake_orch(session_dir: Path) -> SimpleNamespace:
    return SimpleNamespace(
        ctx=SimpleNamespace(
            session_id="t", session_dir=session_dir, event_log=EventLog(), store=None
        ),
        stop_watching=lambda: None,
    )


def _stopped_events(session_dir: Path) -> list:
    return [e for e in EventLog().read(session_dir) if e.type == "orchestrator_stopped"]


def test_block_no_block_emits_user_exactly_once(tmp_path: Path) -> None:
    # no_block returns before the loop; the finally still emits a single {user}.
    block_until_stopped(_fake_orch(tmp_path), "t", no_block=True, manifest=False)
    events = _stopped_events(tmp_path)
    assert len(events) == 1
    assert events[0].payload["reason"] == "user"


def test_block_suppresses_emit_when_marker_present(tmp_path: Path) -> None:
    # A `stop` already recorded the terminal event, so the loop's finally must NOT
    # emit a second one (the marker is the single arbiter).
    request_stop(tmp_path)
    block_until_stopped(_fake_orch(tmp_path), "t", no_block=True, manifest=False)
    assert _stopped_events(tmp_path) == []


def test_block_until_stopped_breaks_on_marker(tmp_path: Path) -> None:
    # The real lifecycle: a backgrounded run's loop observes a marker raised mid-run
    # and exits gracefully (no hang). Marker present in finally -> no emit.
    orch = _fake_orch(tmp_path)
    done = threading.Event()

    def run() -> None:
        block_until_stopped(orch, "t", no_block=False, manifest=False)
        done.set()

    t = threading.Thread(target=run)
    t.start()
    request_stop(tmp_path)
    assert done.wait(timeout=5), "loop did not observe the stop marker"
    t.join(timeout=5)
    assert _stopped_events(tmp_path) == []


def test_block_writes_manifest_on_graceful_stop(
    session_store: SessionStore, tmp_path: Path
) -> None:
    # The manifest=True (non-no_block) branch: a graceful stop writes the result
    # manifest cache. Drive a real store-backed orch and break the loop via marker.
    session_store.create(session_id="g", project_path="c:\\p", psmux_session="g")
    session_dir = session_store.session_dir("g")
    orch = SimpleNamespace(
        ctx=SimpleNamespace(
            session_id="g", session_dir=session_dir,
            event_log=EventLog(), store=session_store,
        ),
        stop_watching=lambda: None,
    )
    done = threading.Event()

    def run() -> None:
        block_until_stopped(orch, "g", no_block=False, manifest=True)
        done.set()

    t = threading.Thread(target=run)
    t.start()
    request_stop(session_dir)
    assert done.wait(timeout=5)
    t.join(timeout=5)
    assert (session_dir / "result_manifest.json").exists()


# --- timeout + kill-panes (S18b2) -------------------------------------------


def _orch_with_psmux(session_store: SessionStore, sid: str, psmux):
    session_store.create(session_id=sid, project_path="c:\\p", psmux_session=f"{sid}-px")
    session_dir = session_store.session_dir(sid)
    return SimpleNamespace(
        ctx=SimpleNamespace(
            session_id=sid, session_dir=session_dir, event_log=EventLog(),
            store=session_store, psmux=psmux,
        ),
        stop_watching=lambda: None,
    ), session_dir


def _killed_session(psmux) -> bool:
    return any("kill-session" in c.args for c in psmux.recorded_calls)


def test_timeout_emits_timeout_reason_and_kills_panes(
    session_store: SessionStore,
) -> None:
    from agent_team.psmux_backend import PsmuxBackend

    psmux = PsmuxBackend(mock=True)
    orch, session_dir = _orch_with_psmux(session_store, "to", psmux)
    block_until_stopped(
        orch, "to", no_block=False, manifest=False, timeout=0.05, kill_panes=False
    )
    events = _stopped_events(session_dir)
    assert len(events) == 1 and events[0].payload["reason"] == "timeout"
    # A timeout is a safety backstop: it kills panes even without --autonomous.
    assert _killed_session(psmux) is True


def test_timeout_projects_to_final_timeout_manifest(
    session_store: SessionStore,
) -> None:
    # End-to-end: a timeout emits orchestrator_stopped{timeout}, which the manifest
    # projection reports as final=True + session_status="timeout" (the contract
    # seam Hermes gates on).
    from agent_team.manifest import load_manifest
    from agent_team.psmux_backend import PsmuxBackend

    orch, session_dir = _orch_with_psmux(session_store, "e2e", PsmuxBackend(mock=True))
    block_until_stopped(
        orch, "e2e", no_block=False, manifest=False, timeout=0.05, kill_panes=False
    )
    m = load_manifest(session_store.load("e2e"), session_dir)
    assert m.final is True
    assert m.session_status == "timeout"


def test_autonomous_kills_panes_on_marker_stop(session_store: SessionStore) -> None:
    from agent_team.psmux_backend import PsmuxBackend

    psmux = PsmuxBackend(mock=True)
    orch, session_dir = _orch_with_psmux(session_store, "au", psmux)
    done = threading.Event()

    def run() -> None:
        block_until_stopped(orch, "au", no_block=False, manifest=False, kill_panes=True)
        done.set()

    t = threading.Thread(target=run)
    t.start()
    request_stop(session_dir)
    assert done.wait(timeout=5)
    t.join(timeout=5)
    assert _killed_session(psmux) is True  # autonomous tears down on terminal stop


def test_attended_marker_stop_does_not_kill_panes(session_store: SessionStore) -> None:
    from agent_team.psmux_backend import PsmuxBackend

    psmux = PsmuxBackend(mock=True)
    orch, session_dir = _orch_with_psmux(session_store, "att", psmux)
    done = threading.Event()

    def run() -> None:
        block_until_stopped(orch, "att", no_block=False, manifest=False, kill_panes=False)
        done.set()

    t = threading.Thread(target=run)
    t.start()
    request_stop(session_dir)
    assert done.wait(timeout=5)
    t.join(timeout=5)
    # Attended stop preserves panes so the human can re-attach / inspect.
    assert _killed_session(psmux) is False


# --- SIGTERM graceful stop (S18b3) ------------------------------------------


def test_signal_emits_signal_reason_and_kills_panes(session_store: SessionStore) -> None:
    # The `_signalled` seam simulates SIGTERM delivery without a real OS signal: a
    # signal stop emits {reason:"signal"} and tears down panes even when attended.
    from agent_team.psmux_backend import PsmuxBackend

    psmux = PsmuxBackend(mock=True)
    orch, session_dir = _orch_with_psmux(session_store, "sig", psmux)
    sig = threading.Event()
    sig.set()
    block_until_stopped(
        orch, "sig", no_block=False, manifest=False, kill_panes=False, _signalled=sig
    )
    events = _stopped_events(session_dir)
    assert len(events) == 1 and events[0].payload["reason"] == "signal"
    assert _killed_session(psmux) is True


def test_install_sigterm_is_noop_off_main_thread() -> None:
    # signal.signal raises ValueError off the main thread -> guarded to (False, None)
    # so the threaded block_until_stopped paths never crash.
    result: dict = {}

    def run() -> None:
        result["out"] = _install_sigterm(lambda *_a: None)

    t = threading.Thread(target=run)
    t.start()
    t.join()
    assert result["out"] == (False, None)


@pytest.mark.skipif(
    sys.platform == "win32", reason="SIGTERM delivery is a no-op on Windows"
)
def test_sigterm_delivery_breaks_loop(session_store: SessionStore) -> None:
    # Real delivery (Linux/macOS): the installed handler flips the flag and the loop
    # exits with reason "signal" — a container/`kill <pid>` stop is now graceful.
    import signal

    from agent_team.psmux_backend import PsmuxBackend

    orch, session_dir = _orch_with_psmux(session_store, "term", PsmuxBackend(mock=True))

    def killer() -> None:
        time.sleep(0.3)
        os.kill(os.getpid(), signal.SIGTERM)

    threading.Thread(target=killer, daemon=True).start()
    block_until_stopped(orch, "term", no_block=False, manifest=False)
    events = _stopped_events(session_dir)
    assert events[-1].payload["reason"] == "signal"


# --- stop command + orphan reaper -------------------------------------------


def test_reap_orphan_panes_kills_via_injected_backend(
    session_store: SessionStore, sessions_base: Path, monkeypatch
) -> None:
    from agent_team.cli.stop import _reap_orphan_panes
    from agent_team.psmux_backend import PsmuxBackend

    monkeypatch.setenv("AGENT_TEAM_HOME", str(sessions_base))
    psmux = PsmuxBackend(mock=True)
    session_store.create(session_id="reap", project_path="c:\\p", psmux_session="reap-px")
    _reap_orphan_panes("reap", backend_factory=lambda: psmux)
    kill = next(c for c in psmux.recorded_calls if "kill-session" in c.args)
    assert "reap-px" in kill.args  # the dead orchestrator's panes are reaped


def test_reap_orphan_panes_swallows_backend_error(
    session_store: SessionStore, sessions_base: Path, monkeypatch
) -> None:
    from agent_team.cli.stop import _reap_orphan_panes
    from agent_team.terminal_backend import BackendNotFoundError

    monkeypatch.setenv("AGENT_TEAM_HOME", str(sessions_base))
    session_store.create(session_id="r2", project_path="c:\\p", psmux_session="r2-px")

    def boom():
        raise BackendNotFoundError("no psmux")

    _reap_orphan_panes("r2", backend_factory=boom)  # best-effort: must not raise


# --- stop command -----------------------------------------------------------


def test_stop_records_event_and_marker(
    session_store: SessionStore, cli_env: dict
) -> None:
    session_store.create(session_id="run", project_path="c:\\p", psmux_session="run")
    result = CliRunner().invoke(main, ["stop", "--session", "run"], env=cli_env)
    assert result.exit_code == 0, result.output
    session_dir = session_store.session_dir("run")
    assert stop_requested(session_dir) is True
    events = _stopped_events(session_dir)
    assert len(events) == 1 and events[0].payload["reason"] == "stopped"


def test_stop_unknown_session_exits_1(cli_env: dict) -> None:
    result = CliRunner().invoke(main, ["stop", "--session", "nope"], env=cli_env)
    assert result.exit_code == 1


# --- stale-marker clear on startup (integration) ----------------------------


def test_attach_clears_stale_stop_marker(
    cli_env: dict, consumer_project: Path, session_store: SessionStore
) -> None:
    # A leftover marker from a prior `stop` must NOT make a fresh attach exit
    # instantly: start/attach clear it before entering the watch loop.
    sid = "restart"
    session_store.create(
        session_id=sid, project_path=str(consumer_project), psmux_session=sid
    )
    session_dir = session_store.session_dir(sid)
    request_stop(session_dir)  # stale marker
    assert stop_requested(session_dir) is True

    result = CliRunner().invoke(
        main, ["attach", "--session", sid, "--dry-run", "--no-psmux", "--no-block"],
        env=cli_env,
    )
    assert result.exit_code == 0, result.output
    assert stop_requested(session_dir) is False  # cleared on startup
