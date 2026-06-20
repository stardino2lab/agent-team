# S11b manual checklist — teammate hardening (D10/D11/D12)

Run on the Windows box with real psmux + real CLIs. Unit tests cover the argv
seam; these confirm the live behavior.

## D10 — transcript capture (pipe-pane)
- [⚠] 2026-06-20 Windows e2e: `transcript.log` IS created per teammate but stayed
      **0 bytes** for the codex teammate (pipe-pane captured nothing). The coordination
      audit (events.jsonl + mailbox) worked, but the per-pane transcript did not. Needs
      a focused D10 live check on Windows (does `pipe-pane -o 'cat >> ...'` capture a
      codex TUI pane? cmd.exe/pwsh `cat`?). Recheck below:
- [ ] Start a session, spawn a claude teammate. Confirm
      `{session_dir}/teammates/<name>/transcript.log` is created AND grows as the
      teammate prints output. (Verifies `cat >> "<path>"` runs under psmux on Windows.)
- [ ] If the redirect command does not work on Windows psmux (e.g. the pane shell
      is cmd.exe, which has no `cat`), note the actual shell the pane uses and the
      working redirect form here: ____________________  Then update
      `PsmuxBackend.pipe_pane`'s `redirect` to the working command BEFORE relying on
      transcripts — the unit test only covers the argv seam, not live capture.
- [ ] `agent-team logs export --session <id> --to <dir>` produces
      `<dir>/events.jsonl` and `<dir>/transcripts/<name>.log`.

## D11 — kickoff input-readiness
- [ ] Spawn a codex teammate (slow first-run startup). Confirm the kickoff is NOT
      dropped — the teammate reads its brief and goes `teammate_ready` without a
      manual re-send. (Pre-D11 this dropped the first keystrokes.)
- [ ] Confirm the readiness wait adds no noticeable delay for a fast claude teammate.

## D11b — kickoff SUBMIT keys, PER PLATFORM (Windows + Linux)
A live e2e ON LINUX found the codex teammate kickoff was typed but never SUBMITTED:
codex's TUI composer did not submit on Enter alone (Tab then Enter was needed), so the
teammate never started, never reached `teammate_ready`/mail, and the pane idled out.
codex's submit behavior DIFFERS BY PLATFORM (confirmed): **Windows codex submits on
Enter alone**; the Linux e2e needed Tab+Enter. So the registry default is `("Enter",)`
(the Windows winner) and Linux drives Tab+Enter via the env override. Isolate the
submit-key variable from the trust-prompt (D12) and readiness (D11).
The runner resolves submit keys via `resolve_teammate_submit_keys(cli)`, overridable
with `AGENT_TEAM_SUBMIT_KEYS_<CLI>` (e.g. `AGENT_TEAM_SUBMIT_KEYS_CODEX="Tab Enter"`) —
so you can try sequences without a rebuild.

Run the whole matrix on BOTH:  ☑ Windows (codex 0.139.0, tmux 3.3.5)   ☐ Linux (codex ___, tmux ___)

### Step A — raw codex submit (NO agent-team; the ground truth)
- [x] Record versions: `codex --version` = 0.139.0 (Windows)  ; `tmux -V` = 3.3.5 (psmux)
- [x] In a psmux/tmux pane run `codex --dangerously-bypass-approvals-and-sandbox`.
      Type a line, press **Enter** alone → does it SUBMIT?  **Windows: YES** (verified
      2026-06-20: typed "Reply with exactly one word: PONG", Enter alone → codex went
      "Working" then replied "PONG"; no trust prompt, folder pre-trusted)  Linux: ___
- [ ] Type a line, press **Tab** then **Enter** → does it SUBMIT?  Windows: n/a (Enter
      already submits)  Linux: ___ (prior e2e: this was the sequence that worked)
- [x] Winning sequence:  **Windows = Enter**  Linux = ____________ (re-confirm; was Tab+Enter)

### Step B — agent-team codex teammate
Full live e2e run on Windows 2026-06-20 (claude lead + agent-team MCP + TUI approve
+ codex implementer teammate, payment-api fixture, isolated AGENT_TEAM_HOME):
- [x] **Windows: PASS (on the 2nd spawn).** Kickoff auto-SUBMITS (Enter), codex reads
      its brief, runs `agent-team teammate ready` → `teammate_ready` event fired
      (helper-2, pane %5), then sends mail `helper-2 -> lead: DONE2`. Full handshake
      works with the Enter default. Linux: ___
- [x] codex reaches `teammate_ready` + mail — **Windows: YES** (events.jsonl +
      mailbox/lead.jsonl confirm). Linux: ___
- [⚠] codex pane survival: the 1st spawn's pane AUTO-TERMINATED — see the update-nag
      blocker below. The 2nd spawn's pane exited normally (task said "then stop").
- Incidental: claude **lead** connected to the agent-team MCP under `--strict-mcp-config`
      and called `spawn_teammate`; TUI approval modal works (approve with lowercase **y**).

> **BLOCKER FOUND — codex update-nag kills the first teammate after a version bump.**
> The 1st codex teammate (0.139.0) launched into codex's INTERACTIVE "✨ Update
> available! → 1. Update now / Press enter to continue" prompt. The readiness wait
> settled on it and the kickoff's **Enter selected "Update now"**, so codex ran
> `npm install -g @openai/codex`, updated 0.139.0→0.141.0, and the pane TERMINATED
> with an empty transcript and no `teammate_ready`. This is the same "pane
> auto-terminates" symptom seen on Linux, but the root cause is the update prompt,
> NOT submit-keys. After codex self-updated to the latest (0.141.0) the nag stopped
> and the retry passed cleanly. **Risk:** every time a new codex version ships, the
> first teammate spawn will hit this and die. No `--no-update-check`/env suppression
> was found in `codex --help` or `~/.codex/config.toml`. FIX (follow-up): suppress
> codex's update check on teammate launch, or have the readiness/kickoff dismiss a
> non-composer startup prompt before sending Enter. Tracked for S14 hardening.

### Step C — claude regression
- [x] claude submits on Enter alone — **Windows: YES** (the lead pane itself: prompt
      typed, Enter, claude processed and called the MCP tool). Linux: ___

### Finalize (after both platforms)
- [x] Set `cli_registry.py` codex `teammate_submit_keys` default to the WINDOWS winner
      = `("Enter",)` (codex override removed; uses the class default). Done 2026-06-20.
- [ ] Linux runs via `AGENT_TEAM_SUBMIT_KEYS_CODEX="Tab Enter"` until S13 adds
      `sys.platform` defaulting (see `docs/s13-next-phase-roadmap.md`). Re-confirm the
      Linux Step A/B on the env-override build (the prior Linux e2e predated it).

## D12 — codex non-interactive
- [x] 2026-06-20 Windows: codex launched in **YOLO mode** with NO per-command approval
      and NO first-run trust prompt (the agent-team folder is pre-trusted in
      `~/.codex/config.toml`; `--dangerously-bypass-approvals-and-sandbox` applied).
      NOTE: trust is satisfied here only because the folder was previously trusted — a
      FRESH folder/machine would still show codex's trust prompt (separate concern).
- [x] The lead never saw/issued any codex flag — it called only the `spawn_teammate`
      MCP tool; the runner applied the codex flags (decoupling invariant intact).
