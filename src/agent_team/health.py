"""Read-time session health derivation (S14a).

Pure, injectable, no I/O in the compute path and NO polling loop — health is
derived at read time from signals the system already writes (member.status,
events.jsonl, the per-teammate transcript mtime, and a live `list_panes` set the
caller passes in). The CLI does the one-shot reads/live query and feeds the data
here; S14b (retry) and S14c (escalation) reuse `derive_member_health`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from agent_team._io import format_ts, parse_ts
from agent_team.event_log import Event
from agent_team.session import Member, Session
from agent_team.spawn_approval import SpawnRequest
from agent_team.tasks import Task

MemberHealthState = Literal[
    "healthy", "starting", "stale", "dead", "error", "unknown"
]

DEFAULT_STALE_AFTER_S = 600


@dataclass
class MemberHealth:
    name: str
    role: str
    cli: str
    status: str
    pane_id: str | None
    health: MemberHealthState
    last_activity: str | None  # ISO ts, or None if no activity signal


@dataclass
class SpawnError:
    """An errored spawn whose request_id has no member row (rejected pre-spawn)."""

    request_id: str | None
    kind: str


@dataclass
class SessionHealth:
    session_id: str
    session_status: str
    members: list[MemberHealth]
    spawn_errors: list[SpawnError]
    task_counts: dict[str, int]
    pending_approval: dict | None
    panes_available: bool
    overall_ok: bool


def errored_request_ids(events: list[Event]) -> tuple[set[str], dict[str, str]]:
    """Request ids whose latest spawn outcome was an unrecovered `error` event.

    A later `teammate_ready` for the same request_id clears it (recovered). Also
    returns the latest error `kind`/`reason` per request_id for reporting.
    """
    state: dict[str, str] = {}
    kinds: dict[str, str] = {}
    for e in events:
        rid = e.payload.get("request_id")
        if rid is None:
            continue
        if e.type == "error":
            state[rid] = "error"
            kinds[rid] = e.payload.get("kind") or e.payload.get("reason") or "error"
        elif e.type == "teammate_ready":
            state[rid] = "ok"
    return {rid for rid, s in state.items() if s == "error"}, kinds


def member_last_activity(
    member: Member,
    *,
    session_dir: Path,
    events: list[Event],
) -> datetime | None:
    """Newest of (an event this member produced) and (its transcript mtime).

    A member "produced" an event when the payload names it as the actor: `name`
    (teammate_ready/shutdown), `from` (mail_sent sender), `assignee` (task_claimed),
    `teammate_name` (forward-compat), or its `request_id`. NOTE `to` is excluded —
    receiving mail is not the recipient being alive. The D6 preamble tells teammates
    not to mail while working, so the transcript mtime is the heartbeat during a long
    quiet task. Returns None when no signal.
    """
    latest: datetime | None = None
    for e in events:
        p = e.payload
        if (
            p.get("name") == member.name
            or p.get("from") == member.name
            or p.get("assignee") == member.name
            or p.get("teammate_name") == member.name
            or (member.request_id is not None and p.get("request_id") == member.request_id)
        ):
            ts = parse_ts(e.ts)
            if latest is None or ts > latest:
                latest = ts
    if member.role == "teammate":
        transcript = session_dir / "teammates" / member.name / "transcript.log"
        try:
            # tz=UTC is REQUIRED: st_mtime is a naive epoch float; comparing a
            # naive-local datetime against a UTC `now` would be off by the local
            # offset (hours), dwarfing stale_after.
            mtime = datetime.fromtimestamp(transcript.stat().st_mtime, tz=UTC)
        except OSError:
            mtime = None
        if mtime is not None and (latest is None or mtime > latest):
            latest = mtime
    return latest


def derive_member_health(
    member: Member,
    *,
    panes: set[str] | None,
    last_activity: datetime | None,
    now: datetime,
    stale_after: float,
    error_request_ids: set[str],
) -> MemberHealthState:
    """Precedence (top-down): error -> starting -> dead -> stale -> unknown -> healthy.

    `starting` short-circuits BEFORE `dead`: a fresh spawn is persisted with a
    pane_id before the pane is guaranteed visible in `list_panes`, so a dead-first
    check would false-positive the spawn race. `dead` needs live `panes`; when
    unavailable (`panes is None`) a running member is `unknown`, never invented-dead.
    `stale` is advisory (activity-based), computable without `panes`.
    """
    if member.status == "error" or (
        member.request_id is not None and member.request_id in error_request_ids
    ):
        return "error"
    if member.status in ("pending", "starting"):
        return "starting"
    if member.pane_id is not None and panes is not None and member.pane_id not in panes:
        return "dead"
    if last_activity is not None and (now - last_activity).total_seconds() > stale_after:
        return "stale"
    if member.pane_id is not None and panes is None:
        return "unknown"
    return "healthy"


def build_session_health(
    session: Session,
    *,
    session_dir: Path,
    panes: set[str] | None,
    events: list[Event],
    tasks: list[Task],
    pending: SpawnRequest | None,
    now: datetime,
    stale_after: float = DEFAULT_STALE_AFTER_S,
) -> SessionHealth:
    """Compose a SessionHealth from already-loaded data (no I/O, no live query).

    `panes` is the live pane-id set (None = liveness unavailable / --no-panes).
    `overall_ok` is False only on a genuine fault (member error/dead or an orphan
    spawn error) — never merely because liveness was unavailable.
    """
    error_rids, kinds = errored_request_ids(events)
    member_rids = {m.request_id for m in session.members if m.request_id is not None}

    members: list[MemberHealth] = []
    for m in session.members:
        la = member_last_activity(m, session_dir=session_dir, events=events)
        health = derive_member_health(
            m,
            panes=panes,
            last_activity=la,
            now=now,
            stale_after=stale_after,
            error_request_ids=error_rids,
        )
        members.append(
            MemberHealth(
                name=m.name,
                role=m.role,
                cli=m.cli,
                status=m.status,
                pane_id=m.pane_id,
                health=health,
                last_activity=format_ts(la) if la is not None else None,
            )
        )

    spawn_errors = [
        SpawnError(request_id=rid, kind=kinds.get(rid, "error"))
        for rid in sorted(error_rids)
        if rid not in member_rids
    ]

    task_counts: dict[str, int] = {}
    for t in tasks:
        task_counts[t.state] = task_counts.get(t.state, 0) + 1

    pending_d = None
    if pending is not None:
        pending_d = {
            "request_id": pending.request_id,
            "persona": pending.persona,
            "requested_at": pending.requested_at,
        }

    bad = any(mh.health in ("error", "dead") for mh in members) or bool(spawn_errors)
    return SessionHealth(
        session_id=session.session_id,
        session_status=session.status,
        members=members,
        spawn_errors=spawn_errors,
        task_counts=task_counts,
        pending_approval=pending_d,
        panes_available=panes is not None,
        overall_ok=not bad,
    )
