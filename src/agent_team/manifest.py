"""Read-only result-manifest projection (S16a).

Composes the existing per-session stores (tasks / session / events / spawn
resolutions / mailbox / escalation) into one task-centric record that an external
upper orchestrator (Hermes) can read back after shelling out to `agent-team`.

Hard rule: **no second source of truth.** Every field is DERIVED at read time
from the stores; `build_manifest` is a pure function over already-loaded data.
The optional on-disk cache (S16b, `result_manifest.json`) is a disposable
convenience for the graceful-exit case — it is regenerable from the stores via
`logs manifest` even after a crash that skipped the cache write.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from agent_team import tasks as tasks_mod
from agent_team._io import utc_now, write_json
from agent_team.escalation import Escalation, derive_escalations
from agent_team.event_log import Event, EventLog
from agent_team.health import build_session_health
from agent_team.mailbox import Message, read_inbox
from agent_team.session import Session
from agent_team.spawn_approval import SpawnApproval, SpawnResolution
from agent_team.tasks import Task

# Unfrozen until a real Hermes consumer exists to validate the schema (S16e);
# bumped when the field set changes. A pin test lands with S16e, like the
# status --json field-set pin (test_status_json_field_set_pinned).
# v2 (S18b2): added `final` + terminal-aware `session_status`.
MANIFEST_VERSION = 2

_ORCHESTRATOR_STOPPED = "orchestrator_stopped"
_TASK_RESULT = "task_result"  # emitted by the deferred S16c hook; read if present
_SESSION_SUMMARY = "session_summary"  # ditto


@dataclass
class TaskRecord:
    task_id: str
    title: str
    input: str  # the task's instruction (Task.description; often "")
    role: str | None  # assignee's persona name (the role label); "lead"; None if unknown
    assignee: str | None
    status: str  # completed | abandoned | blocked | in_progress | pending (DERIVED)
    deps: list[str]
    created_at: str
    updated_at: str
    output: str | None  # task_result hook (S16c) else best-effort last mail from assignee
    decision: dict | None  # {decision, decided_by} from the assignee's spawn resolution
    next_action: str | None  # task_result hook (S16c); null today
    artifact_path: str | None  # task_result hook (S16c); null today


@dataclass
class ManifestMember:
    name: str
    role: str  # persona name, or "lead"/"teammate" for members without a persona
    persona: str | None
    cli: str
    status: str


@dataclass
class ResultManifest:
    manifest_version: int
    session_id: str
    project_path: str
    playbook: str | None
    session_status: str  # terminal reason when final, else raw Session.status
    session_stopped: bool  # derived: an orchestrator_stopped event was recorded
    # S18b2 completion contract: Hermes must act ONLY on final=true (else `logs
    # manifest`, callable any time, would report in-progress tasks as the answer).
    # Currently final == session_stopped, valid because autonomous mode kills all
    # panes on stop and never re-attaches; if interactive re-attach is added,
    # redefine as "latest lifecycle event is orchestrator_stopped, no later activity".
    final: bool
    summary: str | None  # session_summary hook (S16c); null today
    members: list[ManifestMember]
    tasks: list[TaskRecord]
    counts: dict[str, int]  # keyed by DERIVED status (NOT health.task_counts' raw state)
    escalation: list[dict]


def _derive_status(task: Task, *, completed_ids: set[str], session_stopped: bool) -> str:
    """Map raw TaskState (+ session/dep context) to the manifest status vocabulary.

    `abandoned`/`blocked` are NOT stored states — they're derived here, so the
    manifest `counts` differ from health.task_counts (which keys on raw state).
    A dep id absent from the task set counts as not-completed (fail-safe: a task
    waiting on a missing/typo'd dep reads as blocked, never silently pending).
    """
    if task.state == "completed":
        return "completed"
    if task.state == "in_progress":
        return "abandoned" if session_stopped else "in_progress"
    # pending
    if any(dep not in completed_ids for dep in task.deps):
        return "blocked"
    return "pending"


def _member_role(persona: str | None, role: str) -> str:
    # The persona name IS the role label (Member.role is only lead/teammate).
    return persona or role


def _last_mail_body(lead_inbox: list[Message], assignee: str | None) -> str | None:
    if not assignee:
        return None
    from_assignee = [m for m in lead_inbox if m.from_ == assignee]
    return from_assignee[-1].body if from_assignee else None


def build_manifest(
    *,
    session: Session,
    tasks: list[Task],
    events: list[Event],
    resolutions: list[SpawnResolution],
    lead_inbox: list[Message],
    escalations: list[Escalation],
    session_stopped: bool,
    manifest_version: int = MANIFEST_VERSION,
) -> ResultManifest:
    """Pure projection over already-loaded stores — no I/O (escalations are passed
    in because deriving them stats teammate transcripts; see load_manifest)."""
    members_by_name = {m.name: m for m in session.members}
    resolution_by_req = {r.request_id: r for r in resolutions}
    completed_ids = {t.id for t in tasks if t.state == "completed"}

    # Forward-compat: read the deferred S16c hook events if a lead emitted them;
    # latest-wins per task. Absent today -> output/next_action/artifact_path null.
    task_results: dict[str, dict] = {}
    summary: str | None = None
    terminal_reason: str | None = None  # latest orchestrator_stopped reason (S18b2)
    for ev in events:
        if ev.type == _TASK_RESULT:
            tid = ev.payload.get("task_id")
            if tid is not None:
                task_results[tid] = ev.payload
        elif ev.type == _SESSION_SUMMARY:
            summary = ev.payload.get("summary", summary)
        elif ev.type == _ORCHESTRATOR_STOPPED:
            terminal_reason = ev.payload.get("reason", terminal_reason)

    records: list[TaskRecord] = []
    for t in tasks:
        member = members_by_name.get(t.assignee) if t.assignee else None
        role = _member_role(member.persona, member.role) if member is not None else None

        decision: dict | None = None
        if member is not None and member.request_id:
            res = resolution_by_req.get(member.request_id)
            if res is not None:
                # Only approved spawns ever become Members, so in practice this is
                # always {"approved", ...} — denied requests have no task/assignee.
                decision = {"decision": res.decision, "decided_by": res.decided_by}

        hook = task_results.get(t.id, {})
        output = hook.get("output_summary")
        if output is None:
            output = _last_mail_body(lead_inbox, t.assignee)

        records.append(
            TaskRecord(
                task_id=t.id,
                title=t.title,
                input=t.description,
                role=role,
                assignee=t.assignee,
                status=_derive_status(
                    t, completed_ids=completed_ids, session_stopped=session_stopped
                ),
                deps=list(t.deps),
                created_at=t.created_at,
                updated_at=t.updated_at,
                output=output,
                decision=decision,
                next_action=hook.get("next_action"),
                artifact_path=hook.get("artifact_path"),
            )
        )

    counts: dict[str, int] = {}
    for r in records:
        counts[r.status] = counts.get(r.status, 0) + 1

    # When final, surface the terminal reason (never the raw "active", which is the
    # lie the completion contract kills); "stopped" is the safe generic fallback if
    # a stop event lacks a reason.
    session_status = (terminal_reason or "stopped") if session_stopped else session.status

    return ResultManifest(
        manifest_version=manifest_version,
        session_id=session.session_id,
        project_path=session.project_path,
        playbook=session.playbook,
        session_status=session_status,
        session_stopped=session_stopped,
        final=session_stopped,
        summary=summary,
        members=[
            ManifestMember(
                name=m.name,
                role=_member_role(m.persona, m.role),
                persona=m.persona,
                cli=m.cli,
                status=m.status,
            )
            for m in session.members
        ],
        tasks=records,
        counts=counts,
        escalation=[
            {"level": e.level, "subject": e.subject, "reason": e.reason}
            for e in escalations
        ],
    )


def load_manifest(
    session: Session, session_dir: Path, *, now: datetime | None = None
) -> ResultManifest:
    """Read every store and build the manifest. Works post-hoc on a crashed
    session (no result_manifest.json needed) — the stores tolerate torn lines and
    missing dirs. Liveness is unavailable here (panes=None), matching
    `status --no-panes`: members project as `unknown`, not invented-dead."""
    now = now or utc_now()
    task_list = tasks_mod.list_tasks(session_dir)
    events = EventLog().read(session_dir)
    approval = SpawnApproval()
    resolutions = approval.read_resolutions(session_dir)
    lead_inbox = read_inbox(session_dir, "lead")
    session_stopped = any(e.type == _ORCHESTRATOR_STOPPED for e in events)
    health = build_session_health(
        session,
        session_dir=session_dir,
        panes=None,
        events=events,
        tasks=task_list,
        pending=approval.get_pending(session_dir),
        now=now,
    )
    escalations = derive_escalations(health, task_list)
    return build_manifest(
        session=session,
        tasks=task_list,
        events=events,
        resolutions=resolutions,
        lead_inbox=lead_inbox,
        escalations=escalations,
        session_stopped=session_stopped,
    )


def write_manifest_cache(
    session: Session, session_dir: Path, *, now: datetime | None = None
) -> Path:
    """S16b: cache the projection to result_manifest.json (atomic). A disposable
    convenience for graceful exit — NOT the completion contract; Hermes
    regenerates from the stores via `logs manifest` after a crash."""
    manifest = load_manifest(session, session_dir, now=now)
    path = session_dir / "result_manifest.json"
    write_json(path, asdict(manifest))
    return path


# ---- renderers -------------------------------------------------------------

def render_json(manifest: ResultManifest) -> str:
    return json.dumps(asdict(manifest), indent=2, default=str)


def render_jsonl(manifest: ResultManifest) -> str:
    """Task-centric stream: one JSON object per task (envelope/escalation dropped
    by design — use json for the full envelope). Each row carries session_id."""
    rows = []
    for t in manifest.tasks:
        row = asdict(t)
        row["session_id"] = manifest.session_id
        rows.append(json.dumps(row, default=str))
    return "\n".join(rows)


def _md_cell(value: str | None) -> str:
    # Keep GFM table rows on one line and escape the column delimiter.
    return (value or "").replace("|", "\\|").replace("\n", " ").replace("\r", " ").strip()


def render_md(manifest: ResultManifest) -> str:
    final = "  (final)" if manifest.final else ""
    lines = [
        f"# Session {manifest.session_id}",
        "",
        f"- project: {manifest.project_path}",
        f"- playbook: {manifest.playbook or '-'}",
        f"- status: {manifest.session_status}{final}",
    ]
    if manifest.summary:
        lines += ["", f"**Summary:** {_md_cell(manifest.summary)}"]
    counts = " / ".join(f"{n} {state}" for state, n in sorted(manifest.counts.items()))
    lines += ["", f"**Tasks:** {counts or 'none'}", ""]
    lines += [
        "| task | status | role | assignee | title |",
        "| --- | --- | --- | --- | --- |",
    ]
    # list_tasks already orders by numeric task suffix; preserve that order.
    for t in manifest.tasks:
        lines.append(
            f"| {t.task_id} | {t.status} | {t.role or '-'} | "
            f"{t.assignee or '-'} | {_md_cell(t.title)} |"
        )
    if manifest.escalation:
        lines += ["", "## Escalations", ""]
        for e in manifest.escalation:
            lines.append(f"- **{e['level']}** {e['subject']}: {_md_cell(e['reason'])}")
    return "\n".join(lines) + "\n"
