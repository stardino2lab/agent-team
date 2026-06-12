"""Orchestrator: bridges spawn approvals to teammate panes."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from agent_team._watcher import FileWatcher
from agent_team.event_log import EventLog
from agent_team.project_loader import ProjectLoader
from agent_team.psmux_backend import PsmuxBackend
from agent_team.session import Member, Session, SessionStore
from agent_team.spawn_approval import SpawnApproval, SpawnResolution
from agent_team.teammate_runner import TeammateRunner


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

        psmux_session = self.ctx.session_id
        lead = Member(
            name="lead",
            role="lead",
            persona=None,
            cli="claude",
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
                lead_pane = self.ctx.psmux.new_session(psmux_session, cwd=project_path)
                self.ctx.psmux.split_pane(
                    psmux_session,
                    command="python -m agent_team.tui",
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
            # Partial start — wipe the half-built session_dir so the next
            # `start --session SAME` is not blocked by an "already exists"
            # check. Safe in S8 dry-run: nothing real is running yet.
            shutil.rmtree(self.ctx.session_dir, ignore_errors=True)
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
