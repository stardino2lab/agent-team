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

## Enterprise per-command approval routed to Hermes (1B)

- **What:** Let codex/agy teammates run in the enterprise (no-auto-approve) mode by
  routing each tool-call approval to Hermes, instead of the `--dangerously-*`
  auto-approve flags that enterprise bans.
- **Why:** The 1A decision (plan-eng-review 2026-06-25) makes enterprise mode
  claude-teammate-only — codex/agy are personal-mode-only because their teammate
  launch depends on `--dangerously-bypass-approvals-and-sandbox` /
  `--dangerously-skip-permissions`, which enterprise forbids. 1B is the only path
  that brings codex/agy into an enterprise team.
- **Pros:** Unlocks heterogeneous teams under enterprise policy; Hermes already
  owns spawn approval (S18a), so per-command approval is a conceptual extension.
- **Cons:** Highest operational risk of the options considered: every tool call
  round-trips to Hermes (latency + single point of failure if Hermes stalls), and
  each CLI has a different approval protocol (codex sandbox prompts vs agy vs
  claude) → brittle, many edge cases. Weaker compliance story than 1A ("flag
  present but intercepted" is harder to audit than "flag absent").
- **Context:** Start from the S18a external-approver seam (`cli/approvals` +
  `spawn_approval`) and widen it from spawn-time to per-tool-call. The hard part is
  intercepting tool calls at the CLI boundary — codex/agy don't expose a clean
  per-call approval hook the way the spawn gate does. Likely needs an MCP-level or
  pane-driver interception layer. Prove live before trusting it for compliance.
- **Depends on / blocked by:** 1A landing first (mode gate + `resolve_launch_args`);
  a real enterprise requirement to run codex/agy (deferred 2026-06-25 — enterprise
  is claude-team-only until this is genuinely needed).

## Doc-drift guard (automated currency check)

- **What:** A lightweight test that fails when docs drift from code — assert the
  README / `docs/STATUS.ko.md` status-line milestone matches the latest "done"
  row in the milestone-gate table, and that the stated test count matches
  `pytest --co -q`. Higher-value half: enforce the PROGRESS.md ↔ PROGRESS.ko.md
  EN↔KO mirror stays in lockstep.
- **Why:** The 2026-06-22 doc sync found the *canonical* PROGRESS.md claiming
  "410 passed" when reality was 411, and 5 of 8 docs frozen 6+ slices behind the
  code. Manual milestone/test-count tracking rots silently; full-mirror Korean
  now means two deep logs to keep in step.
- **Pros:** Drift becomes a red CI signal instead of a quarterly surprise; cheap
  to run; makes the EN↔KO mirror enforceable, not trust-based.
- **Cons:** A test that must change every milestone can become noise; test-count
  assertions can flap on WIP branches — gate it to a sanity range or run advisory.
- **Context:** Add `tests/test_docs_currency.py` parsing the milestone-gate
  tables in `PROGRESS.md` / `PROGRESS.ko.md` / `docs/STATUS.ko.md` plus the README
  status line. Start with the EN↔KO mirror consistency (highest value), then the
  test-count stamp. See the 2026-06-22 doc-sync (S11→S18 sweep) for the motivating
  drift.
- **Depends on / blocked by:** nothing.
