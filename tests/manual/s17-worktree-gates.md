# S17 worktree isolation gates (G6) — run on THIS Windows box

The worktree lifecycle (create / idempotent-reuse / remove+prune / non-repo error /
read-only-skip) and the orchestrator wiring (isolate on spawn, prune on shutdown,
predictable `worktree_failed` stop) are unit-tested with REAL git
(`test_worktree.py`, `test_orchestrator_worktree.py`, `test_mcp_server.py`). These
gates cover what unit tests cannot model: a real teammate CLI editing in an isolated
tree, two writers not colliding, merge-back, and Windows path/lock behavior.

## Prerequisites
- A consumer project that **is a git repo** with at least one commit
  (`git worktree add HEAD` needs a born HEAD — a brand-new `git init` with no commit
  fails by design; the spawn then emits `error{kind: worktree_failed}`).
- `.agent-team/config.yaml` with `isolate_worktrees: true` and
  `allowed_personas` including `implementer` (and a second write persona for the
  two-writer gate).

## Free checks (no tokens, just a start)
- [ ] Start a session in the git project with `isolate_worktrees: true`. Spawn +
      approve an `implementer` teammate. Confirm `git -C <project> worktree list`
      shows a worktree at `<session_dir>/worktrees/<name>` and the teammate pane's
      cwd is that worktree (not the shared checkout).
- [ ] Spawn a `planner`/`reviewer` (read-only) teammate in the same session →
      **no** worktree is created for it; it runs in the shared project root.
- [ ] Flip `isolate_worktrees: false` (or remove it) → spawned teammates run in the
      shared checkout, no `worktrees/` entries. (Default-off = today's behavior.)
- [ ] Point the session at a NON-git directory with `isolate_worktrees: true`,
      spawn an implementer → the spawn does NOT create a pane; `agent-team logs tail`
      shows `error` with `kind: worktree_failed` (no silent fallback to the shared
      root, no zombie pane).

## Live checks (need real teammate CLIs; spend tokens)
- [ ] **G6-two-writers:** spawn two write-capable teammates; have each edit the SAME
      file in its own worktree. Confirm the edits do not collide in the shared tree
      (each lands in its own worktree HEAD).
- [ ] **G6-merge:** lead/reviewer integrates by merging each worktree's HEAD back to
      the project branch. Confirm a clean merge (or a predictable, surfaced conflict
      — not a silent loss).
- [ ] **G6-prune:** `shutdown_teammate` (or end the session) → the teammate's
      worktree dir is removed and `git -C <project> worktree list` no longer shows it
      (idempotent: re-running prune is a no-op).
- [ ] **G6-no-zombie:** a worktree-creation failure (non-repo / unborn HEAD / git
      missing) leaves NO pane and NO half-created `worktrees/<name>` registered in git.

## Windows-specific risks to watch
- [ ] **Path length:** worktrees live under `~/.claude/.../sessions/<id>/worktrees/<name>`
      plus git's internal `.git/worktrees/<name>` refs — deep. With a long teammate
      name this can approach MAX_PATH (260). If creation fails with a path-length
      error, enable `git config core.longpaths true` / Windows long-path support and
      note it here.
- [ ] **File locks:** confirm a teammate process holding a file open in its worktree
      does not block `git worktree remove --force` on shutdown (remove uses `--force`;
      if a lock still blocks it, the prune is best-effort and the dir may linger —
      record the behavior).
- [ ] **cwd outside project tree:** the worktree is outside the original project dir;
      confirm the teammate CLI's relative tooling (pytest, AGENTS.md discovery, git)
      still resolves correctly from the worktree cwd.

## Notes / limitations (by design in S17)
- Isolation is **opt-in** (attended) and scoped to `workspace-write` personas; it is
  the blast-radius control that makes unattended/autonomous (S18) runs defensible.
- The write-lease fallback and an advisory task `paths` field are **out of scope**
  for this slice (separate follow-up if worktrees prove heavy on Windows).
- Creation failure is a HARD stop (no fallback) — containment must not silently
  degrade to the shared checkout.

## Outcome
- Free checks + G6-two-writers + G6-merge + G6-prune + G6-no-zombie PASS, and no
  Windows path/lock blocker → worktree isolation is trustworthy as the S18 containment
  prerequisite. Record any Windows path-length / lock remedy applied.
