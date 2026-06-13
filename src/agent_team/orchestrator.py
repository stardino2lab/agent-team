"""Orchestrator: bridges spawn approvals to teammate panes."""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from agent_team._watcher import FileWatcher
from agent_team.event_log import EventLog
from agent_team.project_loader import ProjectLoader
from agent_team.psmux_backend import PsmuxBackend
from agent_team.session import Member, Session, SessionStore, default_base_dir
from agent_team.spawn_approval import SpawnApproval, SpawnResolution
from agent_team.teammate_runner import TeammateRunner

_SUPPORTED_LEAD_CLIS: frozenset[str] = frozenset({"claude"})


def _check_lead_cli_supported(cli: str) -> None:
    """Raise early if config asks for a lead CLI S9 cannot launch.

    Kept at start() entry so an unsupported value never gets as far as
    creating a session_dir / psmux session — the user just sees a clean
    NotImplementedError pointing at S11+.
    """
    if cli not in _SUPPORTED_LEAD_CLIS:
        raise NotImplementedError(
            f"Lead CLI {cli!r} not supported yet "
            f"(codex/antigravity planned for S11+)"
        )


def _write_lead_mcp_config(session_dir: Path, session_id: str, project_path: Path) -> Path:
    """Render the lead's MCP config JSON to {session_dir}/claude-mcp.json.

    Uses json.dumps (not Jinja) so Windows backslashes do not need manual
    escaping inside the template. AGENT_TEAM_HOME is captured from
    default_base_dir() at write time — env var changes after this function
    returns do not flow into the file. A fresh `agent-team start` would
    re-render with the new value.
    """
    config = {
        "mcpServers": {
            "agent-team": {
                "command": "python",
                "args": ["-m", "agent_team.mcp_server"],
                "env": {
                    "AGENT_TEAM_HOME": str(default_base_dir()),
                    "AGENT_TEAM_SESSION_ID": session_id,
                    "AGENT_TEAM_PROJECT_PATH": str(project_path.resolve()),
                },
            }
        }
    }
    path = session_dir / "claude-mcp.json"
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path


def _write_lead_system_prompt(session_dir: Path, lead_context_text: str) -> Path:
    """Write the lead system prompt to {session_dir}/lead-system-prompt.md.

    File-based delivery is the only safe channel: the prompt is multi-line
    markdown that may contain shell-meta characters (`$`, backticks, quotes,
    raw newlines). Passing it through psmux send_keys + cmd.exe / PowerShell
    quoting on Windows mangles or breaks the launch line. Claude reads the
    file directly via --append-system-prompt-file so no shell interpretation
    happens.
    """
    path = session_dir / "lead-system-prompt.md"
    path.write_text(lead_context_text, encoding="utf-8")
    return path


def _build_lead_launch_command(
    cli: str, *, mcp_config: Path, system_prompt_file: Path
) -> str:
    """Compose the lead CLI launch line that gets send_keys'd to the lead pane.

    S9 supports claude only. codex / antigravity are S11+ and would add an
    elif branch here (plus their own MCP config template). The seam is
    intentionally narrow so future additions do not touch Orchestrator.start.
    """
    if cli == "claude":
        return (
            f'claude --mcp-config "{mcp_config}" --strict-mcp-config '
            f'--append-system-prompt-file "{system_prompt_file}"'
        )
    raise NotImplementedError(
        f"Lead CLI {cli!r} not supported yet "
        f"(codex/antigravity planned for S11+)"
    )


@dataclass
class OrchestratorContext:
    session_id: str
    session_dir: Path
    store: SessionStore
    approval: SpawnApproval
    runner: TeammateRunner
    psmux: PsmuxBackend
    event_log: EventLog
    no_psmux: bool = False


class Orchestrator:
    """Drains the approval queue and spawns teammates idempotently."""

    def __init__(self, ctx: OrchestratorContext) -> None:
        self.ctx = ctx
        self._handled_request_ids: set[str] = set()
        self._watcher: FileWatcher | None = None

    def start_watching(self) -> None:
        """Start a FileWatcher on approval/ that calls run_once on change."""
        if self._watcher is not None:
            return
        approval_dir = self.ctx.session_dir / "approval"
        approval_dir.mkdir(parents=True, exist_ok=True)
        self._watcher = FileWatcher(
            approval_dir,
            self.run_once,
            label="ResolutionWatcher",
        )
        self._watcher.start()

    def stop_watching(self) -> None:
        if self._watcher is not None:
            self._watcher.stop()
            self._watcher = None

    def start(
        self,
        *,
        project_path: Path,
        playbook: str | None = None,
        context_text: str | None = None,
    ) -> Session:
        loader = ProjectLoader(project_path)
        config = loader.load_config()
        max_teammates = int(config.get("max_teammates", 5))
        playbook_mode = str(config.get("playbook_mode", "guide"))
        lead_cli = str(config.get("lead_cli", "claude"))
        _check_lead_cli_supported(lead_cli)

        psmux_session = self.ctx.session_id
        lead = Member(
            name="lead",
            role="lead",
            persona=None,
            cli=lead_cli,
            pane_id=None,
            backend="psmux",
            status="pending",
        )
        session = self.ctx.store.create(
            session_id=self.ctx.session_id,
            project_path=str(project_path),
            psmux_session=psmux_session,
            playbook=playbook,
            playbook_mode=playbook_mode,
            members=[lead],
            max_teammates=max_teammates,
        )

        try:
            members_started: list[str] = ["lead"]
            if not self.ctx.no_psmux:
                mcp_config_path = _write_lead_mcp_config(
                    self.ctx.session_dir, self.ctx.session_id, project_path
                )
                lead_context = loader.build_lead_context(
                    playbook_name=playbook, extra_context=context_text
                )
                prompt_path = _write_lead_system_prompt(
                    self.ctx.session_dir, lead_context.text
                )
                launch_cmd = _build_lead_launch_command(
                    lead_cli,
                    mcp_config=mcp_config_path,
                    system_prompt_file=prompt_path,
                )
                lead_pane = self.ctx.psmux.new_session(psmux_session, cwd=project_path)
                self.ctx.psmux.send_keys(lead_pane, launch_cmd, enter=True)
                # CLI entry (not `python -m agent_team.tui`) so the session id
                # flows through argv. The module entry needs AGENT_TEAM_SESSION_ID,
                # which psmux.split_pane has no way to inject.
                self.ctx.psmux.split_pane(
                    psmux_session,
                    command=f"agent-team tui --session {self.ctx.session_id}",
                    cwd=project_path,
                )
                lead.pane_id = lead_pane
                lead.status = "running"
                self.ctx.store.update_members(self.ctx.session_id, [lead])
                members_started.append("tui")

            self.ctx.event_log.append(
                self.ctx.session_dir,
                type_="session_started",
                payload={
                    "session_id": self.ctx.session_id,
                    "psmux_session": psmux_session,
                    "playbook": playbook,
                    "playbook_mode": playbook_mode,
                    "members": members_started,
                    "context": context_text,
                },
            )
            self.run_once()
            self.start_watching()
        except Exception:
            # Partial start — tear down both sides of the split brain so the
            # next `start --session SAME` is not blocked by "already exists"
            # on disk or "duplicate session" on psmux.
            if not self.ctx.no_psmux:
                try:
                    self.ctx.psmux.kill_session(psmux_session)
                except Exception as psmux_exc:  # noqa: BLE001
                    print(
                        "Orchestrator.start psmux cleanup failed for "
                        f"{psmux_session!r}: {psmux_exc!r}",
                        file=sys.stderr,
                    )
            try:
                shutil.rmtree(self.ctx.session_dir)
            except OSError as cleanup_exc:
                print(
                    "Orchestrator.start cleanup failed for "
                    f"{self.ctx.session_dir}: {cleanup_exc!r}",
                    file=sys.stderr,
                )
            raise
        return session

    def attach(self) -> Session:
        session = self.ctx.store.load(self.ctx.session_id)
        self.reconcile_handled()
        self.run_once()
        self.start_watching()
        return session

    def reconcile_handled(self) -> None:
        """At attach time, re-derive the handled set from disk state.

        A resolution is treated as handled if any of the following hold:
        - decision is "denied"
        - an emitted teammate_ready or error event carries its request_id
        - its teammate_name already appears in session.members
        The event-log channel is the strongest signal, because teammate_name
        is often None when the request did not pre-assign one.
        """
        ready_request_ids: set[str] = set()
        for event in self.ctx.event_log.read(self.ctx.session_dir):
            if event.type in ("teammate_ready", "error"):
                req_id = event.payload.get("request_id")
                if isinstance(req_id, str):
                    ready_request_ids.add(req_id)

        session = self.ctx.store.load(self.ctx.session_id)
        teammate_names = {m.name for m in session.members if m.role == "teammate"}

        for res in self.ctx.approval.read_resolutions(self.ctx.session_dir):
            if res.decision == "denied":
                self._handled_request_ids.add(res.request_id)
            elif res.request_id in ready_request_ids:
                self._handled_request_ids.add(res.request_id)
            elif res.teammate_name and res.teammate_name in teammate_names:
                self._handled_request_ids.add(res.request_id)

    def run_once(self) -> int:
        spawned = 0
        for res in self.ctx.approval.read_resolutions(self.ctx.session_dir):
            if res.request_id in self._handled_request_ids:
                continue
            if res.decision != "approved":
                self._handled_request_ids.add(res.request_id)
                continue
            if self._spawn_one(res):
                spawned += 1
            self._handled_request_ids.add(res.request_id)
        return spawned

    def _spawn_one(self, res: SpawnResolution) -> bool:
        if res.persona is None or res.cli is None:
            self.ctx.event_log.append(
                self.ctx.session_dir,
                type_="error",
                payload={
                    "kind": "invalid_resolution",
                    "request_id": res.request_id,
                    "missing": [
                        f for f in ("persona", "cli") if getattr(res, f) is None
                    ],
                },
            )
            return False
        session = self.ctx.store.load(self.ctx.session_id)
        existing_teammates = [m.name for m in session.members if m.role == "teammate"]
        teammate_count = len(existing_teammates)
        if teammate_count >= session.max_teammates:
            self.ctx.event_log.append(
                self.ctx.session_dir,
                type_="error",
                payload={
                    "kind": "max_teammates_exceeded",
                    "request_id": res.request_id,
                    "max_teammates": session.max_teammates,
                    "current": teammate_count,
                    "existing_teammates": existing_teammates,
                },
            )
            return False
        teammate_name = res.teammate_name or self._next_teammate_name(session)
        persona = res.persona
        cli = res.cli

        if self.ctx.no_psmux:
            pane_id: str | None = None
        else:
            result = self.ctx.runner.spawn(
                psmux_session=session.psmux_session,
                persona=persona,
                prompt=res.prompt or "",
                teammate_name=teammate_name,
                session_id=session.session_id,
                session_dir=self.ctx.session_dir,
                project_path=Path(session.project_path),
            )
            pane_id = result.pane_id

        members = list(session.members) + [
            Member(
                name=teammate_name,
                role="teammate",
                persona=res.persona,
                cli=cli,
                pane_id=pane_id,
                backend="psmux",
                status="running",
            )
        ]
        self.ctx.store.update_members(session.session_id, members)
        self.ctx.event_log.append(
            self.ctx.session_dir,
            type_="teammate_ready",
            payload={
                "request_id": res.request_id,
                "persona": persona,
                "name": teammate_name,
                "pane_id": pane_id,
                "cli": cli,
            },
        )
        return True

    def _next_teammate_name(self, session: Session) -> str:
        existing = {m.name for m in session.members if m.role == "teammate"}
        i = 1
        while f"helper-{i}" in existing:
            i += 1
        return f"helper-{i}"
