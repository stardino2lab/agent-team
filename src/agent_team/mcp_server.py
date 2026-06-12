"""MCP server exposing team-lead tools over stdio."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from agent_team import tasks
from agent_team._io import InvalidPathSegmentError, safe_segment
from agent_team.event_log import EventLog
from agent_team.mailbox import read_inbox
from agent_team.mailbox import send as mailbox_send
from agent_team.personas import PersonaLoadError, PersonaNotFoundError, PersonaRegistry
from agent_team.project_loader import ProjectConfigError, ProjectLoader
from agent_team.psmux_backend import PsmuxBackend, PsmuxCommandError
from agent_team.session import Member, SessionNotFoundError, SessionStore
from agent_team.spawn_approval import SpawnApproval, SpawnPendingError

mcp = FastMCP("agent-team")


class McpConfigError(RuntimeError):
    """Raised when required MCP environment is missing."""


class McpToolError(RuntimeError):
    """Domain errors surfaced to MCP client as tool error text."""


@dataclass
class McpContext:
    session_id: str
    session_dir: Path
    project_path: Path | None
    store: SessionStore
    registry: PersonaRegistry
    approval: SpawnApproval
    psmux: PsmuxBackend
    event_log: EventLog


def member_to_response(member: Member) -> dict:
    return {
        "name": member.name,
        "role": member.role,
        "persona": member.persona,
        "cli": member.cli,
        "pane_id": member.pane_id,
        "backend": member.backend,
        "status": member.status,
    }


def _require_project(ctx: McpContext) -> Path:
    if ctx.project_path is None:
        raise McpConfigError("AGENT_TEAM_PROJECT_PATH is required")
    return ctx.project_path


def _find_teammate(members: list[Member], name: str) -> Member | None:
    for member in members:
        if member.role == "teammate" and member.name == name:
            return member
    return None


def resolve_context(
    *,
    session_id: str | None = None,
    project_path: str | None = None,
    store: SessionStore | None = None,
    approval: SpawnApproval | None = None,
    psmux: PsmuxBackend | None = None,
    event_log: EventLog | None = None,
    registry: PersonaRegistry | None = None,
) -> McpContext:
    sid = session_id or os.environ.get("AGENT_TEAM_SESSION_ID")
    if not sid:
        raise McpConfigError("AGENT_TEAM_SESSION_ID is required")

    if project_path is not None:
        proj_raw = project_path
    else:
        proj_raw = os.environ.get("AGENT_TEAM_PROJECT_PATH")
    proj = Path(proj_raw) if proj_raw else None

    session_store = store or SessionStore()
    session_store.load(sid)
    session_dir = session_store.session_dir(sid)

    if registry is None:
        registry = PersonaRegistry(project_path=proj) if proj is not None else PersonaRegistry()

    return McpContext(
        session_id=sid,
        session_dir=session_dir,
        project_path=proj,
        store=session_store,
        registry=registry,
        approval=approval or SpawnApproval(),
        psmux=psmux or PsmuxBackend(),
        event_log=event_log or EventLog(),
    )


def _map_tool_error(exc: BaseException) -> str:
    if isinstance(exc, json.JSONDecodeError):
        return "malformed session data"
    if isinstance(
        exc,
        (
            McpConfigError,
            McpToolError,
            SessionNotFoundError,
            PersonaNotFoundError,
            PersonaLoadError,
            SpawnPendingError,
            InvalidPathSegmentError,
            tasks.TaskNotFoundError,
            tasks.TaskDependencyError,
            tasks.TaskStateError,
            ProjectConfigError,
            PsmuxCommandError,
            ValueError,
        ),
    ):
        return str(exc)
    return "Internal tool error"


def handle_list_personas(ctx: McpContext) -> dict:
    project_path = _require_project(ctx)
    config = ProjectLoader(project_path).load_config()
    allowed = config.get("allowed_personas", [])
    personas = ctx.registry.filter_allowed(allowed)
    return {
        "personas": [
            {"name": p.name, "cli": p.cli, "description": p.description} for p in personas
        ]
    }


def handle_spawn_teammate(
    ctx: McpContext,
    persona: str,
    prompt: str,
    name: str | None = None,
) -> dict:
    project_path = _require_project(ctx)
    config = ProjectLoader(project_path).load_config()
    allowed = config.get("allowed_personas", [])
    if not ctx.registry.is_allowed(persona, allowed):
        raise McpToolError(f"Persona not allowed: {persona}")

    session = ctx.store.load(ctx.session_id)
    teammate_count = sum(1 for m in session.members if m.role == "teammate")
    if teammate_count >= session.max_teammates:
        raise McpToolError(f"Max teammates reached: {session.max_teammates}")

    persona_obj = ctx.registry.get(persona)
    req = ctx.approval.request_spawn(
        ctx.session_dir,
        persona=persona,
        cli=persona_obj.cli,
        prompt=prompt,
        requested_by="lead",
        teammate_name=name,
        event_log=ctx.event_log,
    )
    return {"request_id": req.request_id, "status": "pending"}


def handle_shutdown_teammate(ctx: McpContext, name: str) -> dict:
    safe_segment(name, "teammate")
    session = ctx.store.load(ctx.session_id)
    member = _find_teammate(session.members, name)
    if member is None:
        raise McpToolError(f"Teammate not found: {name}")
    if member.pane_id:
        ctx.psmux.kill_pane(member.pane_id)
    updated = [m for m in session.members if m.name != name]
    ctx.store.update_members(ctx.session_id, updated)
    ctx.event_log.append(
        ctx.session_dir,
        type_="teammate_shutdown",
        payload={"name": name},
    )
    return {"name": name, "status": "shutdown"}


def handle_send_message(ctx: McpContext, to: str, body: str) -> dict:
    message = mailbox_send(
        ctx.session_dir,
        from_="lead",
        to=to,
        body=body,
        event_log=ctx.event_log,
    )
    return {"id": message.id, "to": message.to, "ts": message.ts}


def handle_read_messages(ctx: McpContext, since: str | None = None) -> dict:
    messages = read_inbox(ctx.session_dir, "lead", since=since)
    return {
        "messages": [
            {
                "id": m.id,
                "from": m.from_,
                "to": m.to,
                "body": m.body,
                "ts": m.ts,
            }
            for m in messages
        ]
    }


def handle_create_task(
    ctx: McpContext,
    title: str,
    description: str | None = None,
    deps: list[str] | None = None,
) -> dict:
    task = tasks.create_task(
        ctx.session_dir,
        title=title,
        description=description or "",
        deps=deps,
        event_log=ctx.event_log,
    )
    return {"task_id": task.id, "title": task.title, "state": task.state}


def handle_claim_task(
    ctx: McpContext,
    task_id: str,
    assignee: str | None = None,
) -> dict:
    resolved_assignee = assignee or "lead"
    safe_segment(resolved_assignee, "assignee")
    task = tasks.claim_task(
        ctx.session_dir,
        task_id,
        assignee=resolved_assignee,
        event_log=ctx.event_log,
    )
    return {"task_id": task.id, "assignee": task.assignee or resolved_assignee, "state": task.state}


def handle_complete_task(ctx: McpContext, task_id: str) -> dict:
    task = tasks.complete_task(ctx.session_dir, task_id, event_log=ctx.event_log)
    return {"task_id": task.id, "state": task.state}


def handle_list_teammates(ctx: McpContext) -> dict:
    session = ctx.store.load(ctx.session_id)
    return {"members": [member_to_response(m) for m in session.members]}


def _run_tool(handler, *args, **kwargs):
    try:
        ctx = resolve_context()
        return handler(ctx, *args, **kwargs)
    except Exception as exc:
        raise RuntimeError(_map_tool_error(exc)) from exc


@mcp.tool()
def list_personas() -> dict:
    """List personas allowed for this project."""
    return _run_tool(handle_list_personas)


@mcp.tool()
def spawn_teammate(persona: str, prompt: str, name: str | None = None) -> dict:
    """Request spawning a teammate (pending user approval)."""
    return _run_tool(handle_spawn_teammate, persona, prompt, name)


@mcp.tool()
def shutdown_teammate(name: str) -> dict:
    """Shut down a teammate pane and remove from session."""
    return _run_tool(handle_shutdown_teammate, name)


@mcp.tool()
def send_message(to: str, body: str) -> dict:
    """Send a message from lead to a teammate."""
    return _run_tool(handle_send_message, to, body)


@mcp.tool()
def read_messages(since: str | None = None) -> dict:
    """Read lead inbox messages, optionally since an ISO timestamp."""
    return _run_tool(handle_read_messages, since)


@mcp.tool()
def create_task(
    title: str,
    description: str | None = None,
    deps: list[str] | None = None,
) -> dict:
    """Create a task on the shared board."""
    return _run_tool(handle_create_task, title, description, deps)


@mcp.tool()
def claim_task(task_id: str, assignee: str | None = None) -> dict:
    """Claim a pending task."""
    return _run_tool(handle_claim_task, task_id, assignee)


@mcp.tool()
def complete_task(task_id: str) -> dict:
    """Mark a task completed."""
    return _run_tool(handle_complete_task, task_id)


@mcp.tool()
def list_teammates() -> dict:
    """List session members from session.json."""
    return _run_tool(handle_list_teammates)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
