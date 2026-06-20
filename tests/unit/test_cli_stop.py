"""S18b1: graceful `stop` command + block_until_stopped lifecycle."""

from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner

from agent_team.__main__ import main
from agent_team.cli._helpers import (
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
