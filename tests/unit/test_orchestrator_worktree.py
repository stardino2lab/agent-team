"""Orchestrator <-> worktree isolation integration (S17)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from agent_team.event_log import EventLog
from agent_team.orchestrator import Orchestrator, OrchestratorContext
from agent_team.personas import PersonaRegistry
from agent_team.psmux_backend import PsmuxBackend
from agent_team.session import Member, SessionStore
from agent_team.spawn_approval import SpawnApproval
from agent_team.teammate_runner import TeammateRunner

_GIT = shutil.which("git")
requires_git = pytest.mark.skipif(_GIT is None, reason="git not on PATH")


def _git(repo: Path, *args: str) -> None:
    subprocess.run([_GIT, "-C", str(repo), *args], capture_output=True, text=True, check=True)


def _make_project(path: Path, *, isolate: bool, git: bool) -> Path:
    cfg_dir = path / ".agent-team"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "config.yaml").write_text(
        "project_name: p\nmax_teammates: 5\n"
        "allowed_personas:\n  - implementer\n"
        f"isolate_worktrees: {str(isolate).lower()}\n",
        encoding="utf-8",
    )
    if git:
        _git(path, "init")
        _git(path, "-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "--allow-empty", "-m", "init")
    return path


def _orchestrator(
    sid: str, project: Path, store: SessionStore,
    psmux: PsmuxBackend, registry: PersonaRegistry, log: EventLog,
) -> Orchestrator:
    store.create(
        session_id=sid, project_path=str(project), psmux_session=sid,
        members=[Member(name="lead", role="lead", persona=None, cli="claude",
                        pane_id="%0", backend="psmux", status="running")],
    )
    psmux.new_session(sid)
    ctx = OrchestratorContext(
        session_id=sid, session_dir=store.session_dir(sid), store=store,
        approval=SpawnApproval(),
        runner=TeammateRunner(psmux, registry, mock=False),
        psmux=psmux, event_log=log,
    )
    return Orchestrator(ctx)


def _approve(orch: Orchestrator, log: EventLog, persona: str) -> None:
    req = orch.ctx.approval.request_spawn(
        orch.ctx.session_dir, persona=persona, cli="codex", prompt="build",
        requested_by="lead", teammate_name="impl-1", event_log=log,
    )
    orch.ctx.approval.approve(orch.ctx.session_dir, req.request_id,
                              decided_by="user", event_log=log)


@requires_git
def test_spawn_isolates_workspace_write_teammate_in_worktree(
    tmp_path: Path, session_store: SessionStore, psmux_backend: PsmuxBackend,
    persona_registry: PersonaRegistry, event_log: EventLog,
) -> None:
    project = _make_project(tmp_path / "proj", isolate=True, git=True)
    orch = _orchestrator("iso", project, session_store, psmux_backend,
                         persona_registry, event_log)
    _approve(orch, event_log, "implementer")  # workspace-write persona

    assert orch.run_once() == 1
    wt = orch.ctx.session_dir / "worktrees" / "impl-1"
    assert wt.exists(), "worktree should be created for an isolated teammate"
    # The teammate pane launches IN the worktree, not the shared checkout.
    split = next(c for c in psmux_backend.recorded_calls if "split-window" in c.args)
    assert split.cwd == str(wt.resolve())


@requires_git
def test_spawn_failure_when_worktree_cannot_be_created(
    tmp_path: Path, session_store: SessionStore, psmux_backend: PsmuxBackend,
    persona_registry: PersonaRegistry, event_log: EventLog,
) -> None:
    # isolate_worktrees:true but the project is NOT a git repo -> create fails ->
    # predictable hard stop (no member, no fallback to the shared root).
    project = _make_project(tmp_path / "proj", isolate=True, git=False)
    orch = _orchestrator("noiso", project, session_store, psmux_backend,
                         persona_registry, event_log)
    _approve(orch, event_log, "implementer")

    assert orch.run_once() == 0  # spawn did not produce a member
    session = session_store.load("noiso")
    assert all(m.role != "teammate" for m in session.members)
    errors = [e for e in event_log.read(orch.ctx.session_dir) if e.type == "error"]
    assert any(e.payload.get("kind") == "worktree_failed" for e in errors)


@requires_git
def test_read_only_persona_not_isolated_even_when_flag_on(
    tmp_path: Path, session_store: SessionStore, psmux_backend: PsmuxBackend,
    persona_registry: PersonaRegistry, event_log: EventLog,
) -> None:
    project = _make_project(tmp_path / "proj", isolate=True, git=True)
    # allow planner (read-only-first) too
    (project / ".agent-team" / "config.yaml").write_text(
        "project_name: p\nmax_teammates: 5\n"
        "allowed_personas:\n  - planner\nisolate_worktrees: true\n",
        encoding="utf-8",
    )
    orch = _orchestrator("ro", project, session_store, psmux_backend,
                         persona_registry, event_log)
    _approve(orch, event_log, "planner")

    assert orch.run_once() == 1
    # No worktree for a read-only persona; it runs in the shared checkout.
    assert not (orch.ctx.session_dir / "worktrees" / "impl-1").exists()
    split = next(c for c in psmux_backend.recorded_calls if "split-window" in c.args)
    assert split.cwd == str(project.resolve())
