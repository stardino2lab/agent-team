"""agent-team status - one-shot read-only session health snapshot (S14a)."""

from __future__ import annotations

import json

import click

from agent_team import tasks as tasks_mod
from agent_team._io import utc_now
from agent_team.cli._helpers import CLI_ERRORS, echo_error, resolve_base_dir
from agent_team.escalation import Escalation, derive_escalations
from agent_team.event_log import EventLog
from agent_team.health import SessionHealth, build_session_health
from agent_team.session import SessionStore
from agent_team.spawn_approval import SpawnApproval
from agent_team.terminal_backend import (
    BackendCommandError,
    BackendNotFoundError,
    make_terminal_backend,
)

# Exit code for "command ran, team is unhealthy" — distinct from echo_error's 1
# ("the command itself failed", e.g. bad session id), so scripts/gates/Hermes can
# tell a dead teammate from a usage error.
_EXIT_UNHEALTHY = 2


def _health_to_dict(h: SessionHealth, escalations: list[Escalation]) -> dict:
    return {
        "session_id": h.session_id,
        "session_status": h.session_status,
        "panes_available": h.panes_available,
        "overall_ok": h.overall_ok,
        "escalations": [
            {"level": e.level, "subject": e.subject, "reason": e.reason}
            for e in escalations
        ],
        "members": [
            {
                "name": m.name,
                "role": m.role,
                "cli": m.cli,
                "status": m.status,
                "pane_id": m.pane_id,
                "health": m.health,
                "last_activity": m.last_activity,
            }
            for m in h.members
        ],
        "spawn_errors": [
            {"request_id": e.request_id, "kind": e.kind} for e in h.spawn_errors
        ],
        "task_counts": h.task_counts,
        "pending_approval": h.pending_approval,
    }


def _render_text(h: SessionHealth, escalations: list[Escalation]) -> None:
    panes_note = "" if h.panes_available else "  (pane liveness unavailable)"
    click.echo(
        f"session {h.session_id}  status={h.session_status}  "
        f"ok={h.overall_ok}{panes_note}"
    )
    for m in h.members:
        last = m.last_activity or "-"
        click.echo(
            f"  {m.name:<12} {m.cli:<8} {m.status:<9} "
            f"pane={m.pane_id or '-':<4} {m.health.upper():<8} last={last}"
        )
    for e in h.spawn_errors:
        click.echo(f"  spawn-error {e.request_id}: {e.kind}")
    for esc in escalations:
        click.echo(f"  escalation[{esc.level}] {esc.subject}: {esc.reason}")
    counts = " / ".join(f"{n} {state}" for state, n in sorted(h.task_counts.items()))
    click.echo(f"tasks: {counts or 'none'}")
    if h.pending_approval is not None:
        p = h.pending_approval
        click.echo(
            f"pending approval: {p['request_id']} ({p['persona']}) "
            f"requested {p['requested_at']}"
        )


@click.command("status")
@click.option("--session", "session_id", required=True, help="Session id")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output")
@click.option(
    "--no-panes",
    is_flag=True,
    help="Skip the live pane-liveness query (file-only; dead detection disabled)",
)
def status_cmd(session_id: str, as_json: bool, no_panes: bool) -> None:
    """Show a one-shot health snapshot for a session (exits 2 if unhealthy)."""
    health: SessionHealth | None = None
    try:
        store = SessionStore(base_dir=resolve_base_dir())
        session = store.load(session_id)
        session_dir = store.session_dir(session_id)

        panes: set[str] | None = None
        if not no_panes:
            # Both backend construction (missing exe) AND list_panes (session gone)
            # can raise; either -> liveness unavailable, not a crash and not
            # "everything dead" (a control-plane failure must never invent deadness).
            try:
                backend = make_terminal_backend()
                panes = {p.pane_id for p in backend.list_panes(session.psmux_session)}
            except (BackendNotFoundError, BackendCommandError, ValueError):
                # ValueError = a bad AGENT_TEAM_BACKEND value; degrade to
                # liveness-unavailable rather than failing the command.
                panes = None

        task_list = tasks_mod.list_tasks(session_dir)
        health = build_session_health(
            session,
            session_dir=session_dir,
            panes=panes,
            events=EventLog().read(session_dir),
            tasks=task_list,
            pending=SpawnApproval().get_pending(session_dir),
            now=utc_now(),
        )
        escalations = derive_escalations(health, task_list)

        if as_json:
            click.echo(
                json.dumps(_health_to_dict(health, escalations), indent=2, default=str)
            )
        else:
            _render_text(health, escalations)
    except CLI_ERRORS as exc:
        echo_error(str(exc))

    if health is not None and not health.overall_ok:
        raise SystemExit(_EXIT_UNHEALTHY)
