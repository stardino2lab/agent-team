"""External-approver CLI (S18a).

Lets an upstream orchestrator (Hermes) inspect and resolve spawn approvals
WITHOUT a human at the TUI. The spawn gate itself is unchanged — every spawn is
still resolved by an approver before it runs; only the approver is allowed to be
a program. `decided_by` attributes the approver (human vs hermes) in the audit
trail, and `SpawnApproval.approve/deny` produce the exact same resolutions.jsonl
+ event + cleared-pending state a TUI approval would, so the orchestrator's
run_once spawns identically.
"""

from __future__ import annotations

import json

import click

from agent_team.cli._helpers import CLI_ERRORS, echo_error, resolve_session_dir
from agent_team.event_log import EventLog
from agent_team.spawn_approval import SpawnApproval, SpawnRequest


def _pending_to_dict(pending: SpawnRequest | None) -> dict:
    if pending is None:
        return {"pending": None}
    # prompt_preview (truncated), never the full prompt — an approve/deny decision
    # doesn't need it and it can be large. request_id/persona/requested_at field
    # names match status --json's pending_approval so the two surfaces don't diverge.
    return {
        "pending": {
            "request_id": pending.request_id,
            "persona": pending.persona,
            "cli": pending.cli,
            "prompt_preview": pending.prompt_preview,
            "teammate_name": pending.teammate_name,
            "requested_by": pending.requested_by,
            "requested_at": pending.requested_at,
        }
    }


@click.group("approvals")
def approvals_group() -> None:
    """Inspect and resolve pending spawn approvals (external approver)."""


@approvals_group.command("list")
@click.option("--session", required=True)
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output")
def list_cmd(session: str, as_json: bool) -> None:
    """Show the current pending spawn request (single-pending-approval gate)."""
    try:
        session_dir = resolve_session_dir(session)
        pending = SpawnApproval().get_pending(session_dir)
        if as_json:
            click.echo(json.dumps(_pending_to_dict(pending), default=str))
        elif pending is None:
            click.echo("no pending spawn request")
        else:
            click.echo(
                f"{pending.request_id}  {pending.persona} ({pending.cli})  "
                f"requested_by={pending.requested_by}  at {pending.requested_at}"
            )
    except CLI_ERRORS as exc:
        echo_error(str(exc))


def _resolve(session: str, request_id: str, decided_by: str, *, deny: bool) -> None:
    try:
        session_dir = resolve_session_dir(session)
        approval = SpawnApproval()
        log = EventLog()
        if deny:
            res = approval.deny(
                session_dir, request_id, decided_by=decided_by, event_log=log
            )
        else:
            res = approval.approve(
                session_dir, request_id, decided_by=decided_by, event_log=log
            )
        click.echo(f"{res.decision} {res.request_id} by {res.decided_by}")
    except CLI_ERRORS as exc:
        echo_error(str(exc))


@approvals_group.command("approve")
@click.option("--session", required=True)
@click.option("--id", "request_id", required=True, help="Pending request id (apr-NNN)")
@click.option(
    "--by",
    "decided_by",
    default="user",
    show_default=True,
    help="Approver identity recorded in the audit trail (e.g. hermes)",
)
def approve_cmd(session: str, request_id: str, decided_by: str) -> None:
    """Approve a pending spawn; the spawn proceeds as a TUI approval would."""
    _resolve(session, request_id, decided_by, deny=False)


@approvals_group.command("deny")
@click.option("--session", required=True)
@click.option("--id", "request_id", required=True, help="Pending request id (apr-NNN)")
@click.option(
    "--by",
    "decided_by",
    default="user",
    show_default=True,
    help="Approver identity recorded in the audit trail (e.g. hermes)",
)
def deny_cmd(session: str, request_id: str, decided_by: str) -> None:
    """Deny a pending spawn request."""
    _resolve(session, request_id, decided_by, deny=True)
