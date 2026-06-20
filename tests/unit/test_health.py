"""health.py: read-time health derivation (S14a)."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from agent_team._io import format_ts, utc_now
from agent_team.event_log import Event
from agent_team.health import (
    build_session_health,
    derive_member_health,
    errored_request_ids,
    member_last_activity,
)
from agent_team.session import Member, Session
from agent_team.spawn_approval import SpawnRequest
from agent_team.tasks import Task

NOW = utc_now()


def _member(
    name="helper-1",
    *,
    role="teammate",
    status="running",
    pane_id="%1",
    request_id=None,
    cli="codex",
) -> Member:
    return Member(
        name=name,
        role=role,
        persona="implementer",
        cli=cli,
        pane_id=pane_id,
        backend="psmux",
        status=status,
        request_id=request_id,
    )


def _derive(member, *, panes=None, last_activity=None, stale_after=600, errors=None):
    return derive_member_health(
        member,
        panes=panes,
        last_activity=last_activity,
        now=NOW,
        stale_after=stale_after,
        error_request_ids=errors or set(),
    )


# --- derive_member_health truth table ---------------------------------------


def test_error_from_member_status() -> None:
    assert _derive(_member(status="error")) == "error"


def test_error_from_unrecovered_event() -> None:
    m = _member(status="running", request_id="apr-3")
    assert _derive(m, errors={"apr-3"}) == "error"


def test_starting_status_is_starting() -> None:
    assert _derive(_member(status="starting")) == "starting"
    assert _derive(_member(status="pending", pane_id=None)) == "starting"


def test_starting_short_circuits_before_dead() -> None:
    # Fresh spawn: pane_id set, pane not yet in list_panes — must NOT read 'dead'.
    assert _derive(_member(status="starting", pane_id="%9"), panes=set()) == "starting"


def test_dead_when_pane_absent() -> None:
    assert _derive(_member(pane_id="%1"), panes={"%0"}) == "dead"


def test_stale_when_activity_old() -> None:
    old = NOW - timedelta(seconds=700)
    assert _derive(_member(pane_id="%0"), panes={"%0"}, last_activity=old) == "stale"


def test_unknown_when_panes_unavailable() -> None:
    fresh = NOW - timedelta(seconds=5)
    assert _derive(_member(pane_id="%0"), panes=None, last_activity=fresh) == "unknown"


def test_healthy_when_pane_alive_and_fresh() -> None:
    fresh = NOW - timedelta(seconds=5)
    assert _derive(_member(pane_id="%0"), panes={"%0"}, last_activity=fresh) == "healthy"


def test_running_without_pane_id_is_healthy() -> None:
    # no_psmux mode: running member, no pane to check, no activity -> healthy.
    assert _derive(_member(pane_id=None), panes={"%0"}) == "healthy"


def test_stale_computable_without_panes() -> None:
    old = NOW - timedelta(seconds=700)
    assert _derive(_member(pane_id="%0"), panes=None, last_activity=old) == "stale"


def test_dead_beats_stale_when_pane_absent_and_activity_old() -> None:
    # A dead pane that ALSO has old activity must read 'dead', not 'stale' —
    # overall_ok only faults on error/dead, so a precedence flip would hide it.
    old = NOW - timedelta(seconds=700)
    assert _derive(_member(pane_id="%1"), panes={"%0"}, last_activity=old) == "dead"


# --- errored_request_ids ----------------------------------------------------


def test_errored_request_ids_recovered_by_later_ready() -> None:
    events = [
        Event(type="error", ts=format_ts(NOW), payload={"request_id": "apr-1", "kind": "boom"}),
        Event(type="teammate_ready", ts=format_ts(NOW), payload={"request_id": "apr-1"}),
        Event(type="error", ts=format_ts(NOW), payload={"request_id": "apr-2", "reason": "max"}),
    ]
    rids, kinds = errored_request_ids(events)
    assert rids == {"apr-2"}
    assert kinds["apr-2"] == "max"


# --- member_last_activity ---------------------------------------------------


def test_last_activity_from_event_by_name(tmp_path: Path) -> None:
    # `name` is the key teammate_ready/teammate_shutdown actually emit.
    ev = [Event(type="teammate_ready", ts=format_ts(NOW), payload={"name": "helper-1"})]
    assert member_last_activity(_member(), session_dir=tmp_path, events=ev) is not None


def test_last_activity_from_event_by_teammate_name(tmp_path: Path) -> None:
    ev = [Event(type="x", ts=format_ts(NOW), payload={"teammate_name": "helper-1"})]
    assert member_last_activity(_member(), session_dir=tmp_path, events=ev) is not None


def test_last_activity_from_mail_sender_and_assignee(tmp_path: Path) -> None:
    # A teammate's own mail (from) and task claim (assignee) count as its activity;
    # receiving mail (to) does NOT.
    sender = [Event(type="mail_sent", ts=format_ts(NOW), payload={"from": "helper-1"})]
    assert member_last_activity(_member(), session_dir=tmp_path, events=sender) is not None
    claim = [Event(type="task_claimed", ts=format_ts(NOW), payload={"assignee": "helper-1"})]
    assert member_last_activity(_member(), session_dir=tmp_path, events=claim) is not None
    recv = [Event(type="mail_sent", ts=format_ts(NOW), payload={"from": "lead", "to": "helper-1"})]
    assert member_last_activity(_member(), session_dir=tmp_path, events=recv) is None


def test_last_activity_event_newer_than_transcript(tmp_path: Path) -> None:
    # max() must pick the newer signal: an event NOW beats a 900s-old transcript.
    tdir = tmp_path / "teammates" / "helper-1"
    tdir.mkdir(parents=True)
    transcript = tdir / "transcript.log"
    transcript.write_text("old\n", encoding="utf-8")
    old = (NOW - timedelta(seconds=900)).timestamp()
    os.utime(transcript, (old, old))
    ev = [Event(type="teammate_ready", ts=format_ts(NOW), payload={"name": "helper-1"})]
    la = member_last_activity(_member(), session_dir=tmp_path, events=ev)
    assert la is not None
    assert abs((NOW - la).total_seconds()) < 120  # event won, not the old mtime


def test_last_activity_from_event_by_request_id(tmp_path: Path) -> None:
    m = _member(request_id="apr-7")
    ev = [Event(type="teammate_ready", ts=format_ts(NOW), payload={"request_id": "apr-7"})]
    assert member_last_activity(m, session_dir=tmp_path, events=ev) is not None


def test_last_activity_none_when_no_signal(tmp_path: Path) -> None:
    assert member_last_activity(_member(), session_dir=tmp_path, events=[]) is None


def test_last_activity_uses_transcript_mtime(tmp_path: Path) -> None:
    tdir = tmp_path / "teammates" / "helper-1"
    tdir.mkdir(parents=True)
    transcript = tdir / "transcript.log"
    transcript.write_text("work output\n", encoding="utf-8")
    # Transcript newer than the (absent) events -> last_activity comes from mtime.
    la = member_last_activity(_member(), session_dir=tmp_path, events=[])
    assert la is not None
    # Within a few seconds of now (catches a naive-vs-UTC timezone bug, which would
    # be off by the whole local offset).
    assert abs((NOW - la).total_seconds()) < 120


def test_last_activity_missing_transcript_no_crash(tmp_path: Path) -> None:
    # teammate dir absent -> stat() OSError swallowed, falls back to events/None.
    assert member_last_activity(_member(), session_dir=tmp_path, events=[]) is None


# --- build_session_health ---------------------------------------------------


def _session(members) -> Session:
    return Session(
        session_id="s",
        project_path="c:\\x",
        psmux_session="s",
        playbook=None,
        playbook_mode="guide",
        created_at=format_ts(NOW),
        status="active",
        members=members,
        max_teammates=5,
    )


def _task(state) -> Task:
    return Task(
        id="task-1",
        title="t",
        description="",
        state=state,
        deps=[],
        assignee="helper-1",
        created_at=format_ts(NOW),
        updated_at=format_ts(NOW),
    )


def test_build_health_counts_and_pending(tmp_path: Path) -> None:
    session = _session([_member(pane_id="%0")])
    pending = SpawnRequest(
        request_id="apr-1",
        persona="planner",
        cli="claude",
        prompt="x",
        prompt_preview="x",
        teammate_name=None,
        requested_by="lead",
        requested_at=format_ts(NOW),
    )
    h = build_session_health(
        session,
        session_dir=tmp_path,
        panes={"%0"},
        events=[],
        tasks=[_task("completed"), _task("pending")],
        pending=pending,
        now=NOW,
    )
    assert h.task_counts == {"completed": 1, "pending": 1}
    assert h.pending_approval["request_id"] == "apr-1"
    assert h.panes_available is True
    assert h.overall_ok is True


def test_build_health_dead_lead_makes_unhealthy(tmp_path: Path) -> None:
    lead = _member(name="lead", role="lead", status="running", pane_id="%0", cli="claude")
    session = _session([lead])
    h = build_session_health(
        session, session_dir=tmp_path, panes=set(), events=[], tasks=[],
        pending=None, now=NOW,
    )
    assert h.members[0].health == "dead"
    assert h.overall_ok is False


def test_build_health_orphan_spawn_error(tmp_path: Path) -> None:
    # An error event whose request_id has no member row -> spawn_errors, unhealthy.
    session = _session([_member(pane_id="%0")])
    events = [
        Event(
            type="error",
            ts=format_ts(NOW),
            payload={"request_id": "apr-99", "kind": "max_teammates_exceeded"},
        )
    ]
    h = build_session_health(
        session, session_dir=tmp_path, panes={"%0"}, events=events, tasks=[],
        pending=None, now=NOW,
    )
    assert any(e.request_id == "apr-99" for e in h.spawn_errors)
    assert h.overall_ok is False


def test_build_health_panes_unavailable_not_forced_unhealthy(tmp_path: Path) -> None:
    session = _session([_member(pane_id="%0", request_id=None)])
    h = build_session_health(
        session, session_dir=tmp_path, panes=None, events=[], tasks=[],
        pending=None, now=NOW,
    )
    assert h.panes_available is False
    assert h.members[0].health == "unknown"
    assert h.overall_ok is True  # unavailability is not a fault
