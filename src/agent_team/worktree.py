"""Per-teammate git worktree isolation (S17 — containment / blast-radius control).

When a project sets ``isolate_worktrees: true``, each write-capable
("implementer-class") teammate gets its own ``git worktree`` under the session
dir as its working directory, instead of editing the shared project checkout.
This is the cheapest real containment for auto-approve teammates (required for
unattended/autonomous S18 runs); the lead/reviewer integrates via merge.

All git access shells out (no library dep), mirroring psmux_backend's subprocess
style. Failures raise WorktreeError — the orchestrator treats a creation failure
as a hard, predictable spawn stop (NO silent fallback to the shared root, which
would defeat containment).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from agent_team._io import safe_segment
from agent_team.personas import Persona

_STDERR_MAX = 500


class WorktreeError(RuntimeError):
    """A git worktree operation failed (git missing, not a repo, unborn HEAD, …)."""


def should_isolate(persona: Persona, config: dict) -> bool:
    """Isolate only write-capable personas, and only when the project opts in.

    `tools_hint == "workspace-write"` is exactly the implementer-class set
    (implementer / tester / agy-implementer / agy-tester); read-only and
    read-only-first personas (planner / reviewer / agy-planner) never isolate —
    they don't edit files, so a worktree would only hide the others' work.
    """
    return bool(config.get("isolate_worktrees", False)) and (
        persona.tools_hint == "workspace-write"
    )


def worktree_path(session_dir: Path, teammate_name: str) -> Path:
    """Deterministic worktree location so shutdown can prune without extra state.

    `teammate_name` is path-validated (same guard as the MCP handlers) so a
    crafted name can't escape the session dir."""
    safe_segment(teammate_name, "teammate")
    return session_dir / "worktrees" / teammate_name


def _run_git(project_path: Path, args: list[str]) -> subprocess.CompletedProcess:
    git = shutil.which("git")
    if git is None:
        raise WorktreeError("git not found on PATH; cannot isolate worktrees")
    try:
        return subprocess.run(
            [git, "-C", str(Path(project_path)), *args],
            shell=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:  # git vanished between which() and run(), perms, etc.
        raise WorktreeError(f"git invocation failed: {exc}") from exc


def _registered_worktrees(project_path: Path) -> set[Path]:
    result = _run_git(project_path, ["worktree", "list", "--porcelain"])
    if result.returncode != 0:
        return set()
    paths: set[Path] = set()
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            paths.add(Path(line[len("worktree ") :].strip()).resolve())
    return paths


def create_worktree(project_path: Path, wt_dir: Path) -> Path:
    """Create (or reuse) a detached worktree at `wt_dir`, returning it.

    Idempotent: a surviving, still-registered worktree (a bounded spawn retry or
    an attach re-running the spawn) is reused rather than re-added, so isolation
    never turns a transient pane error into a permanent spawn failure.
    """
    project_path = Path(project_path)
    wt_dir = Path(wt_dir)
    if wt_dir.exists() and wt_dir.resolve() in _registered_worktrees(project_path):
        return wt_dir
    # Not a reusable live worktree. Self-heal both orphan directions left by a
    # crash so the spawn re-creates cleanly instead of hard-failing on re-entry:
    #   - a registry entry whose dir is gone  -> `worktree prune` drops it;
    #   - a leftover dir no longer registered  -> remove it (it is agent-team-owned,
    #     under the session dir, so deletion is safe).
    _run_git(project_path, ["worktree", "prune"])
    if wt_dir.exists():
        shutil.rmtree(wt_dir, ignore_errors=True)
    wt_dir.parent.mkdir(parents=True, exist_ok=True)
    # --detach: the teammate works on a detached HEAD at the project's current
    # commit; the lead/reviewer integrates by merging the worktree's HEAD. Fails
    # cleanly on a non-repo or an unborn HEAD (brand-new repo, no commits yet).
    result = _run_git(project_path, ["worktree", "add", "--detach", str(wt_dir), "HEAD"])
    if result.returncode != 0:
        stderr = (result.stderr or "")[:_STDERR_MAX]
        raise WorktreeError(
            f"failed to create worktree at {wt_dir} (git exit {result.returncode}): {stderr}"
        )
    return wt_dir


def remove_worktree(project_path: Path, wt_dir: Path) -> bool:
    """Prune a teammate's worktree (idempotent). Returns True if `git worktree
    remove` succeeded; always runs `prune` afterward — even when remove failed
    (e.g. the dir was manually deleted) — so the repo's registry never leaks a
    dead entry."""
    project_path = Path(project_path)
    wt_dir = Path(wt_dir)
    removed = _run_git(
        project_path, ["worktree", "remove", "--force", str(wt_dir)]
    ).returncode == 0
    _run_git(project_path, ["worktree", "prune"])
    return removed
