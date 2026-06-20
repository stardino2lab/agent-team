# S18c — headless autonomous E2E gate (G5)

The capstone of the autonomy track: prove agent-team runs **end-to-end with zero
human interaction** on a **headless Linux host** (no controlling TTY), driven and
resolved by a Hermes-role script. Every piece below is unit-tested in isolation;
this gate verifies they compose live under a real detached tmux + real CLIs.

Extends **S13c** (tmux/Linux) and depends on: **S18a** (external approver),
**S18b1/b2/b3** (stop / timeout / kill-all-panes / SIGTERM / reaper / final flag),
**S17** (worktree containment — REQUIRED for autonomy), **S14** (liveness),
**S16a/b** (result manifest).

## Host preconditions
- [ ] Headless Linux (no `$DISPLAY`, no controlling TTY), tmux ≥ 3.4 installed.
- [ ] At least one teammate CLI authenticated (claude and/or codex). **agy has no
      sandbox option — keep agy teammates OUT of unattended sessions, or run the
      whole session in a container/VM** (see the CRITICAL framing in the roadmap).
- [ ] A consumer project that is a git repo with ≥1 commit, `.agent-team/config.yaml`
      with `isolate_worktrees: true` (containment is required for autonomy) and a
      cost-sane `allowed_personas`.
- [ ] **Globally-unique session id** (mint a uuid suffix — the `project.name`
      default collides on Hermes retries).

## The Hermes-role driver (one script, no human)
A shell script that plays Hermes — it must run to completion with NO interactive input:
- [ ] **Start, backgrounded, autonomous, with a mandatory timeout:**
      `agent-team start --project <repo> --session <uuid> --autonomous --timeout <N> &`
      Confirm it does NOT block the script and the lead pane comes up in a detached
      tmux pane with no TTY.
- [ ] **Watch for pending spawns without polling the orchestrator:**
      `agent-team logs tail --session <uuid> --follow` (or `approvals list --json`)
      surfaces each `spawn_requested`.
- [ ] **Resolve every spawn as the external approver:**
      `agent-team approvals approve --session <uuid> --id <apr> --by hermes`
      (or `deny`). Confirm the teammate spawns with NO TUI ever opened, attributed
      `decided_by: "hermes"` in `resolutions.jsonl`.
- [ ] **Wait for completion the honest way — on `final`, not task state:**
      poll `agent-team logs manifest --session <uuid> --format json` and act ONLY
      when `final: true`. Confirm a mid-run read shows `final: false` (Hermes must
      not act on it).
- [ ] **Read the result manifest** and confirm `session_status` is the terminal
      reason (`timeout`/`stopped`/`signal`/`user`), tasks/decisions/escalations are
      populated, and (if a teammate hung) `escalation` surfaces it.

## Terminal-path coverage (run each variant)
- [ ] **Timeout path:** let `--timeout` expire → `orchestrator_stopped{timeout}`,
      every pane killed, `final: true`, `session_status: "timeout"`, exit 0.
- [ ] **Explicit stop:** `agent-team stop --session <uuid>` mid-run → graceful exit,
      panes reaped, `final: true`, `session_status: "stopped"`.
- [ ] **SIGTERM (container/orchestrator stop):** `kill -TERM <start-pid>` →
      `orchestrator_stopped{signal}`, panes killed, manifest written, exit 0.
- [ ] **Crash + reap:** `kill -9` the orchestrator (orphan panes survive) → Hermes
      runs `agent-team stop` → orphaned teammates reaped; `agent-team logs manifest`
      still yields a valid manifest (pure projection, no cache needed).

## Risks to watch (record findings)
- [ ] **PTY requirement:** interactive CLIs (claude/codex/agy) may need a pty even
      detached — tmux allocates one per pane; confirm each CLI is happy with a
      headless pty (no "not a tty" failure, kickoff send-keys lands).
- [ ] **Containment holds:** each `workspace-write` teammate edits ONLY its
      worktree; the main checkout is untouched until the lead/reviewer merges.
- [ ] **Quota/auth:** one shared `~/.claude`/`~/.codex` is shared quota + a
      same-sid collision risk — true parallel autonomous sessions need isolated
      auth dirs. Note if hit.
- [ ] **Cross-process approve lock:** the `approve` CLI writes `resolutions.jsonl`
      from a separate process; confirm no lost/torn resolution under rapid
      approve+spawn (the reader tolerates torn lines; a file lock on `approval/` is
      the hardening if a race is observed).

## Outcome — Gate G5
- [ ] **G5 PASSED:** a full start → external-approve → work → terminal-stop →
      read-`final`-manifest cycle completes on a headless Linux host with ZERO human
      interaction, containment intact, across the timeout/stop/SIGTERM/crash
      variants. This certifies agent-team as the unattended worker under Hermes
      (the prerequisite for S16e, the frozen Hermes contract doc).
