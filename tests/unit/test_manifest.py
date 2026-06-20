"""manifest.py: read-only result-manifest projection (S16a/b)."""

from __future__ import annotations

import json
from pathlib import Path

from agent_team import tasks as tasks_mod
from agent_team._io import utc_now
from agent_team.escalation import Escalation
from agent_team.event_log import Event, EventLog
from agent_team.mailbox import Message
from agent_team.manifest import (
    MANIFEST_VERSION,
    build_manifest,
    load_manifest,
    render_json,
    render_jsonl,
    render_md,
    write_manifest_cache,
)
from agent_team.session import Member, Session, SessionStore
from agent_team.spawn_approval import SpawnResolution
from agent_team.tasks import Task


def _member(name, *, persona=None, role="teammate", request_id=None, cli="codex") -> Member:
    return Member(
        name=name, role=role, persona=persona, cli=cli, pane_id="%1",
        backend="psmux", status="running", request_id=request_id,
    )


def _session(members, *, status="active") -> Session:
    return Session(
        session_id="s1", project_path="c:\\proj", psmux_session="s1",
        playbook="new-feature", playbook_mode="guide", created_at="t",
        status=status, members=members, max_teammates=5,
    )


def _task(tid, state, *, assignee=None, deps=None) -> Task:
    return Task(
        id=tid, title=f"title {tid}", description=f"do {tid}", state=state,
        deps=deps or [], assignee=assignee, created_at="t0", updated_at="t1",
    )


def _build(session, tasks, **kw):
    return build_manifest(
        session=session,
        tasks=tasks,
        events=kw.get("events", []),
        resolutions=kw.get("resolutions", []),
        lead_inbox=kw.get("lead_inbox", []),
        escalations=kw.get("escalations", []),
        session_stopped=kw.get("session_stopped", False),
    )


# --- status derivation ------------------------------------------------------


def test_status_completed_and_pending() -> None:
    s = _session([_member("lead", role="lead")])
    m = _build(s, [_task("task-1", "completed"), _task("task-2", "pending")])
    by_id = {t.task_id: t for t in m.tasks}
    assert by_id["task-1"].status == "completed"
    assert by_id["task-2"].status == "pending"


def test_in_progress_is_abandoned_only_when_session_stopped() -> None:
    s = _session([_member("h1")])
    running = _build(s, [_task("task-1", "in_progress")], session_stopped=False)
    assert running.tasks[0].status == "in_progress"
    stopped = _build(s, [_task("task-1", "in_progress")], session_stopped=True)
    assert stopped.tasks[0].status == "abandoned"


def test_pending_with_unmet_dep_is_blocked() -> None:
    s = _session([_member("h1")])
    tasks = [_task("task-1", "in_progress"), _task("task-2", "pending", deps=["task-1"])]
    m = _build(s, tasks)
    by_id = {t.task_id: t for t in m.tasks}
    assert by_id["task-2"].status == "blocked"  # dep task-1 not completed


def test_pending_with_completed_dep_is_pending() -> None:
    s = _session([_member("h1")])
    tasks = [_task("task-1", "completed"), _task("task-2", "pending", deps=["task-1"])]
    m = _build(s, tasks)
    by_id = {t.task_id: t for t in m.tasks}
    assert by_id["task-2"].status == "pending"


def test_missing_dep_is_blocked_fail_safe() -> None:
    # A dep id absent from the task set counts as not-completed -> blocked, never
    # silently pending (and never a crash).
    s = _session([_member("h1")])
    m = _build(s, [_task("task-2", "pending", deps=["task-ghost"])])
    assert m.tasks[0].status == "blocked"


# --- role / decision / output derivation ------------------------------------


def test_role_is_assignee_persona_lead_or_none() -> None:
    members = [_member("lead", role="lead"), _member("impl-1", persona="agy-implementer")]
    s = _session(members)
    tasks = [
        _task("task-1", "completed", assignee="impl-1"),
        _task("task-2", "completed", assignee="lead"),
        _task("task-3", "pending", assignee="ghost"),
        _task("task-4", "pending", assignee=None),
    ]
    by_id = {t.task_id: t for t in _build(s, tasks).tasks}
    assert by_id["task-1"].role == "agy-implementer"
    assert by_id["task-2"].role == "lead"  # lead member has no persona
    assert by_id["task-3"].role is None  # unknown assignee
    assert by_id["task-4"].role is None  # unassigned


def test_decision_joins_assignee_spawn_resolution() -> None:
    members = [_member("impl-1", persona="implementer", request_id="apr-1")]
    s = _session(members)
    res = SpawnResolution(
        request_id="apr-1", decision="approved", decided_at="t", decided_by="hermes",
        persona="implementer", cli="codex", prompt="p", teammate_name="impl-1",
        requested_by="lead",
    )
    m = _build(s, [_task("task-1", "in_progress", assignee="impl-1")], resolutions=[res])
    assert m.tasks[0].decision == {"decision": "approved", "decided_by": "hermes"}


def test_decision_none_without_request_id() -> None:
    s = _session([_member("lead", role="lead")])
    m = _build(s, [_task("task-1", "completed", assignee="lead")])
    assert m.tasks[0].decision is None


def test_output_falls_back_to_last_mail_from_assignee() -> None:
    s = _session([_member("impl-1", persona="implementer")])
    inbox = [
        Message(id="1", from_="impl-1", to="lead", body="first", ts="t1"),
        Message(id="2", from_="other", to="lead", body="noise", ts="t2"),
        Message(id="3", from_="impl-1", to="lead", body="done!", ts="t3"),
    ]
    m = _build(s, [_task("task-1", "completed", assignee="impl-1")], lead_inbox=inbox)
    assert m.tasks[0].output == "done!"  # latest from the assignee, not "other"


def test_task_result_hook_preferred_over_mail() -> None:
    s = _session([_member("impl-1", persona="implementer")])
    inbox = [Message(id="1", from_="impl-1", to="lead", body="mail", ts="t1")]
    ev = Event(
        type="task_result", ts="t2",
        payload={"task_id": "task-1", "output_summary": "hook output",
                 "next_action": "deploy", "artifact_path": "out/report.md"},
    )
    rec = _build(
        s, [_task("task-1", "completed", assignee="impl-1")],
        lead_inbox=inbox, events=[ev],
    ).tasks[0]
    assert rec.output == "hook output"
    assert rec.next_action == "deploy"
    assert rec.artifact_path == "out/report.md"


def test_forward_compat_fields_null_without_hooks() -> None:
    s = _session([_member("impl-1", persona="implementer")])
    rec = _build(s, [_task("task-1", "completed", assignee="impl-1")]).tasks[0]
    assert rec.output is None
    assert rec.next_action is None
    assert rec.artifact_path is None


# --- envelope / counts / summary --------------------------------------------


def test_counts_keyed_by_derived_status() -> None:
    s = _session([_member("h1")])
    tasks = [
        _task("task-1", "completed"),
        _task("task-2", "in_progress"),  # -> abandoned (stopped)
        _task("task-3", "pending", deps=["task-2"]),  # -> blocked
    ]
    m = _build(s, tasks, session_stopped=True)
    assert m.counts == {"completed": 1, "abandoned": 1, "blocked": 1}


def test_summary_from_session_summary_event() -> None:
    s = _session([_member("lead", role="lead")])
    ev = Event(type="session_summary", ts="t", payload={"summary": "all done"})
    m = _build(s, [], events=[ev])
    assert m.summary == "all done"


def test_escalations_and_members_in_envelope() -> None:
    s = _session([_member("h1", persona="implementer", cli="codex")])
    esc = [Escalation(level="teammate", subject="h1", reason="dead")]
    m = _build(s, [], escalations=esc)
    assert m.manifest_version == MANIFEST_VERSION
    assert m.escalation == [{"level": "teammate", "subject": "h1", "reason": "dead"}]
    assert m.members[0].role == "implementer"
    assert m.members[0].cli == "codex"


def test_empty_session_projects_with_defaults() -> None:
    # Backward-compat: a session with no tasks/events/members still projects.
    s = _session([])
    m = _build(s, [])
    assert m.tasks == []
    assert m.counts == {}
    assert m.summary is None
    assert m.session_id == "s1"


def test_old_session_shape_projects_with_nulls() -> None:
    # Pre-S10b/pre-S13 session: members carry no request_id, no playbook. The
    # manifest must project (null decision/playbook), not crash.
    member = Member(
        name="impl-1", role="teammate", persona="implementer", cli="codex",
        pane_id="%1", backend="psmux", status="running", request_id=None,
    )
    s = Session(
        session_id="old", project_path="c:\\proj", psmux_session="old",
        playbook=None, playbook_mode="guide", created_at="t", status="active",
        members=[member], max_teammates=5,
    )
    m = _build(s, [_task("task-1", "completed", assignee="impl-1")])
    assert m.playbook is None
    assert m.tasks[0].decision is None  # no request_id -> no spawn resolution
    assert m.tasks[0].role == "implementer"


# --- renderers --------------------------------------------------------------


def _sample_manifest():
    s = _session([_member("impl-1", persona="implementer")])
    tasks = [
        _task("task-1", "completed", assignee="impl-1"),
        _task("task-2", "pending", deps=["task-1"]),
    ]
    esc = [Escalation(level="user", subject="apr-9", reason="spawn failed")]
    return _build(s, tasks, escalations=esc)


def test_render_json_roundtrips() -> None:
    data = json.loads(render_json(_sample_manifest()))
    assert data["session_id"] == "s1"
    assert data["manifest_version"] == MANIFEST_VERSION
    assert len(data["tasks"]) == 2
    assert data["escalation"][0]["subject"] == "apr-9"


def test_render_jsonl_one_task_per_line_with_session_id() -> None:
    lines = render_jsonl(_sample_manifest()).splitlines()
    assert len(lines) == 2  # one per task, envelope omitted by design
    rows = [json.loads(line) for line in lines]
    assert all(r["session_id"] == "s1" for r in rows)
    assert {r["task_id"] for r in rows} == {"task-1", "task-2"}


def test_render_md_has_table_and_escapes_pipe() -> None:
    s = _session([_member("impl-1", persona="implementer")])
    t = Task(
        id="task-1", title="add a | b feature", description="", state="completed",
        deps=[], assignee="impl-1", created_at="t", updated_at="t",
    )
    md = render_md(_build(s, [t]))
    assert "| task | status | role | assignee | title |" in md
    assert "add a \\| b feature" in md  # pipe escaped so the GFM table is intact
    assert "task-1" in md


# --- load_manifest / cache (I/O) --------------------------------------------


def _seed_session(store: SessionStore) -> tuple[Session, Path]:
    session = store.create(
        session_id="live", project_path="c:\\proj", psmux_session="live",
        members=[
            Member(name="lead", role="lead", persona=None, cli="claude",
                   pane_id="%0", backend="psmux", status="running"),
            Member(name="impl-1", role="teammate", persona="implementer", cli="codex",
                   pane_id="%1", backend="psmux", status="running",
                   request_id="apr-1"),
        ],
    )
    return session, store.session_dir("live")


def test_load_manifest_reads_stores(session_store: SessionStore) -> None:
    session, session_dir = _seed_session(session_store)
    log = EventLog()
    t = tasks_mod.create_task(session_dir, title="build", description="impl it",
                              event_log=log)
    tasks_mod.claim_task(session_dir, t.id, assignee="impl-1", event_log=log)

    m = load_manifest(session, session_dir, now=utc_now())
    rec = m.tasks[0]
    assert rec.assignee == "impl-1"
    assert rec.role == "implementer"
    assert rec.status == "in_progress"  # claimed, session not stopped
    assert m.session_stopped is False


def test_load_manifest_marks_abandoned_after_stop(session_store: SessionStore) -> None:
    session, session_dir = _seed_session(session_store)
    log = EventLog()
    t = tasks_mod.create_task(session_dir, title="build", description="x", event_log=log)
    tasks_mod.claim_task(session_dir, t.id, assignee="impl-1", event_log=log)
    log.append(session_dir, type_="orchestrator_stopped",
               payload={"session_id": "live", "reason": "user"})

    m = load_manifest(session, session_dir, now=utc_now())
    assert m.session_stopped is True
    assert m.tasks[0].status == "abandoned"


def test_write_manifest_cache_matches_projection(session_store: SessionStore) -> None:
    session, session_dir = _seed_session(session_store)
    log = EventLog()
    tasks_mod.create_task(session_dir, title="build", description="x", event_log=log)
    log.append(session_dir, type_="orchestrator_stopped",
               payload={"session_id": "live", "reason": "user"})

    now = utc_now()
    path = write_manifest_cache(session, session_dir, now=now)
    assert path == session_dir / "result_manifest.json"
    cached = json.loads(path.read_text(encoding="utf-8"))
    fresh = json.loads(render_json(load_manifest(session, session_dir, now=now)))
    assert cached == fresh  # the cache is exactly the on-demand projection


def test_load_manifest_works_without_any_tasks_or_cache(session_store: SessionStore) -> None:
    # The crash/post-hoc path: no result_manifest.json, no tasks, no events.
    session, session_dir = _seed_session(session_store)
    m = load_manifest(session, session_dir, now=utc_now())
    assert m.tasks == []
    assert (session_dir / "result_manifest.json").exists() is False
