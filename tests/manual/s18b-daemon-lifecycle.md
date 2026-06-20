# S18b daemon lifecycle gates

Covers the start-and-walk-away lifecycle. S18b1 (this slice) = graceful `stop` +
exit code + the shared `block_until_stopped` loop honoring a stop marker. S18b2
(terminal states + mandatory `--timeout` + kill-all-panes + manifest `final`) and
S18b3 (signal-handler manifest + orphan-pane reaper) extend this doc as they land.

## S18b1 — graceful stop + exit code
- [ ] `agent-team start --project <repo> --session <sid>` in one terminal (it
      blocks, driving approvals). In another terminal run
      `agent-team stop --session <sid>` → the `start` process exits within ~1s
      with **exit code 0**, prints nothing alarming, and `events.jsonl` has a
      SINGLE `orchestrator_stopped` with `reason: "stopped"` (no duplicate from
      the start process — the marker suppresses its own emit).
- [ ] `result_manifest.json` is written on the graceful stop (start passes
      manifest=True); `agent-team logs manifest --session <sid>` shows
      `session_stopped: true`.
- [ ] Ctrl-C the `start` process instead → single `orchestrator_stopped` with
      `reason: "user"`, exit 0.
- [ ] **Restart after stop:** `agent-team attach --session <sid>` after a prior
      `stop` must run normally (NOT exit instantly) — the stale `control/stop`
      marker is cleared on startup. Confirm the orchestrator stays up until the
      next stop/Ctrl-C.
- [ ] `agent-team stop --session <bad-id>` → exit 1, clean message (no traceback).
- [ ] Backgrounded run: `agent-team start ... &` then `agent-team stop ...` →
      the backgrounded job ends cleanly (the Hermes "start, walk away, stop" loop).

## S18b2 — timeout + terminal states + kill-all-panes (unit-covered; verify live)
- [ ] `agent-team start ... --autonomous` WITHOUT `--timeout` → exits 1 fast
      ("--autonomous requires --timeout"), no panes spawned.
- [ ] `agent-team start ... --timeout 5` (no `--autonomous`) on a real session →
      at ~5s the run emits `orchestrator_stopped{reason:"timeout"}`, kills every
      pane (`git`/edits stop), exits 0. (Timeout always tears down — it's the
      safety backstop, even attended.)
- [ ] `agent-team start ... --autonomous --timeout <n>` → on ANY terminal stop
      (timeout / `agent-team stop` / Ctrl-C) every pane is killed.
- [ ] Attended `start` (no `--autonomous`, no `--timeout`) Ctrl-C → panes are NOT
      killed (human can re-attach/inspect — unchanged behavior).
- [ ] `agent-team logs manifest --session <id>` after a terminal stop →
      `final: true` and `session_status` is the terminal reason
      (timeout/stopped/user); while running → `final: false`, status `active`.
      Confirm Hermes can gate on `final` (mid-run reads show `final:false`).

## Pending (S18b3 — land with that slice)
- [ ] Crash-safe terminal manifest from a signal handler (SIGTERM), not only the
      `finally`; a SIGKILL'd orchestrator still yields a valid manifest via
      `logs manifest` (pure projection).
- [ ] Orphan-pane reaper: on attach/restart, panes left by a dead orchestrator are
      detected and `kill_session`ed (auto-approve teammates must not edit headless).

## Notes
- The supported "daemon" mode is the foreground blocking run backgrounded by the
  caller (`start &`) + `stop` to end it — there is no separate fork/daemonize.
- `--no-block` remains a hidden TEST seam (returns immediately, tears down); it is
  not the autonomous run mode.
- Concurrency: autonomous mode needs globally-unique session ids (the
  `project.name` default collides on Hermes retries) and a file lock on
  `approval/` for the cross-process `approve` — tracked in S18b/concurrency.

## Outcome
- S18b1 PASS = graceful stop ends a backgrounded run with exit 0, one terminal
  event, a manifest, and a clean restart → the lifecycle is ready for S18b2's
  timeout/terminal-state contract.
