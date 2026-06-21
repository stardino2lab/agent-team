# TODOS

Deferred work items. Each captures enough context to pick up cold.

## Teammate transcript redirect when pane shell is not PowerShell

- **What:** Make `pipe_pane`'s transcript redirect work when a teammate pane's
  default shell on Windows is NOT PowerShell (e.g. cmd.exe).
- **Why:** The S18 fix (`PsmuxBackend._pipe_redirect_cmd`) emits a PowerShell
  stdin→file command. It assumes the pane shell is PowerShell (true on the dev
  box). If a user's default shell is cmd.exe, the PowerShell command won't run
  and `transcript.log` goes back to 0 bytes → empty work log + STALE false
  positive (the exact bug S18 just fixed, re-opened under a different shell).
- **Pros:** Robust across Windows shell configs; removes a silent-failure trap.
- **Cons:** Shell detection adds branching/complexity for a case not yet hit;
  detecting the pane's actual shell from psmux is non-trivial.
- **Context:** Root cause is that `psmux pipe-pane -o <cmd>` runs `<cmd>` in the
  pane's shell. S18 split the redirect by backend class
  (`PsmuxBackend`=PowerShell, `TmuxBackend`=unix `cat >>`). A third axis (Windows
  shell variant) is not handled. Likely fix: detect the pane shell or emit a
  shell-agnostic redirect (e.g. force `cmd /c "findstr ^ >> path"` or invoke
  `powershell -NoProfile -Command`). Verify live like the S18 spike. See
  `src/agent_team/psmux_backend.py` `pipe_pane`, `tests/manual/s14-status-gates.md`.
- **Depends on / blocked by:** S18 1A transcript fix landing first.

## Hermes headless-autonomous lead readiness

- **What:** Make the claude LEAD runnable with zero human input so Hermes can
  drive a fully unattended session on Ubuntu.
- **Why:** Today the lead is bare-launched: on a fresh folder it blocks on the
  first-run "trust this folder?" modal, and even after that it sits idle until a
  human types an initial message. Both were hit live in the G1 gate. Under Hermes
  (no human), the lead would hang at the trust modal and never start.
- **Pros:** Unlocks the G5 headless-autonomous capstone and real Hermes usage.
- **Cons:** Auto-trust + auto-kickoff reduce the human safety gate on the lead;
  must be opt-in (autonomous mode only), not the attended default.
- **Context:** Two changes needed: (1) launch the lead with a trust-bypass
  (claude `--dangerously-skip-permissions` or pre-seeded per-folder trust) when
  `--autonomous`; (2) auto-send the lead an initial kickoff message after boot
  (the orchestrator currently only send_keys the launch command, not a first
  turn — see orchestrator.start ~line 391-392; teammates already get a kickoff
  via teammate_runner). Then run the G5 headless gate (tests/manual/s18c-headless.md).
  Attended mode keeps the manual trust + manual first turn unchanged.
- **Depends on / blocked by:** decision to pursue unattended/Hermes (deferred
  2026-06-22 in favor of attended-first); codex submit-keys Linux default landing.
