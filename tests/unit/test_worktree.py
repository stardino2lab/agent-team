"""worktree.py: per-teammate git worktree isolation (S17)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from agent_team._io import InvalidPathSegmentError
from agent_team.personas import Persona
from agent_team.worktree import (
    WorktreeError,
    _registered_worktrees,
    create_worktree,
    remove_worktree,
    should_isolate,
    worktree_path,
)

_GIT = shutil.which("git")
requires_git = pytest.mark.skipif(_GIT is None, reason="git not on PATH")


def _persona(tools_hint: str | None) -> Persona:
    return Persona(
        name="x", cli="codex", description="d", spawn_prompt_template="p",
        tools_hint=tools_hint,
    )


# --- should_isolate ---------------------------------------------------------


def test_should_isolate_off_by_default() -> None:
    assert should_isolate(_persona("workspace-write"), {}) is False
    assert should_isolate(_persona("workspace-write"), {"isolate_worktrees": False}) is False


def test_should_isolate_only_workspace_write() -> None:
    cfg = {"isolate_worktrees": True}
    assert should_isolate(_persona("workspace-write"), cfg) is True  # implementer/tester
    assert should_isolate(_persona("read-only"), cfg) is False  # reviewer/agy-planner
    assert should_isolate(_persona("read-only-first"), cfg) is False  # planner
    assert should_isolate(_persona(None), cfg) is False


# --- worktree_path ----------------------------------------------------------


def test_worktree_path_is_under_session_dir(tmp_path: Path) -> None:
    assert worktree_path(tmp_path, "impl-1") == tmp_path / "worktrees" / "impl-1"


def test_worktree_path_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(InvalidPathSegmentError):
        worktree_path(tmp_path, "../evil")


# --- create / remove (real git) ---------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_GIT, "-C", str(repo), *args], capture_output=True, text=True, check=True
    )


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init")
    # commit-ish must resolve for `worktree add HEAD`; one empty commit is enough.
    _git(path, "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "--allow-empty", "-m", "init")
    return path


@requires_git
def test_create_worktree_registers_and_remove_prunes(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    wt = tmp_path / "session" / "worktrees" / "impl-1"

    create_worktree(repo, wt)
    assert wt.exists()
    assert wt.resolve() in _registered_worktrees(repo)

    assert remove_worktree(repo, wt) is True
    assert not wt.exists()
    assert wt.resolve() not in _registered_worktrees(repo)


@requires_git
def test_create_worktree_is_idempotent(tmp_path: Path) -> None:
    # A bounded spawn retry / attach re-running the spawn must not hard-fail on an
    # already-created worktree.
    repo = _init_repo(tmp_path / "repo")
    wt = tmp_path / "session" / "worktrees" / "impl-1"
    first = create_worktree(repo, wt)
    second = create_worktree(repo, wt)  # would raise "path exists" if not idempotent
    assert first == second == wt


@requires_git
def test_remove_worktree_idempotent_when_already_gone(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    wt = tmp_path / "session" / "worktrees" / "impl-1"
    # Never created: remove returns False but does not raise (prune still runs).
    assert remove_worktree(repo, wt) is False


@requires_git
def test_create_worktree_self_heals_orphan_dir(tmp_path: Path) -> None:
    # A leftover dir from a crashed run (exists on disk, NOT a registered worktree)
    # must not hard-fail re-spawn: create_worktree cleans it and re-creates.
    repo = _init_repo(tmp_path / "repo")
    wt = tmp_path / "session" / "worktrees" / "impl-1"
    wt.mkdir(parents=True)
    (wt / "leftover.txt").write_text("stale", encoding="utf-8")

    create_worktree(repo, wt)  # self-heals instead of raising "path exists"
    assert wt.resolve() in _registered_worktrees(repo)


@requires_git
def test_create_worktree_on_non_repo_raises(tmp_path: Path) -> None:
    not_a_repo = tmp_path / "plain"
    not_a_repo.mkdir()
    with pytest.raises(WorktreeError):
        create_worktree(not_a_repo, tmp_path / "wt")
