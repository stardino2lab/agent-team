# S11b manual checklist — teammate hardening (D10/D11/D12)

Run on the Windows box with real psmux + real CLIs. Unit tests cover the argv
seam; these confirm the live behavior.

## D10 — transcript capture (pipe-pane)
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
The fix `CliSpec.teammate_submit_keys` (codex `("Tab","Enter")`, default `("Enter",)`)
carries the LINUX value as PROVISIONAL — Windows (the primary target) is UNVERIFIED.
codex's submit behavior may differ by OS and/or codex version, so VERIFY EACH PLATFORM
and isolate the submit-key variable from the trust-prompt (D12) and readiness (D11).
The runner resolves submit keys via `resolve_teammate_submit_keys(cli)`, overridable
with `AGENT_TEAM_SUBMIT_KEYS_<CLI>` (e.g. `AGENT_TEAM_SUBMIT_KEYS_CODEX="Tab Enter"`) —
so you can try sequences without a rebuild.

Run the whole matrix on BOTH:  ☐ Windows (codex 0.139.0, psmux)   ☐ Linux (codex ___, tmux ___)

### Step A — raw codex submit (NO agent-team; the ground truth)
- [ ] Record versions: `codex --version` = ______  ; `tmux -V` / psmux = ______
- [ ] In a psmux/tmux pane run `codex --dangerously-bypass-approvals-and-sandbox`.
      Type a line, press **Enter** alone → does it SUBMIT?  Windows: ___  Linux: ___
- [ ] Type a line, press **Tab** then **Enter** → does it SUBMIT?  Windows: ___  Linux: ___
- [ ] Winning sequence:  Windows = ____________  Linux = ____________

### Step B — agent-team codex teammate
- [ ] Spawn a codex teammate with submit keys = the Step-A winner (set
      `AGENT_TEAM_SUBMIT_KEYS_CODEX` if it differs from the `("Tab","Enter")` default).
- [ ] Kickoff auto-SUBMITS — codex starts working (reads brief, runs `agent-team
      teammate ready`) with NO manual nudge.  Windows: ___  Linux: ___
- [ ] codex reaches `teammate_ready` + sends mail.  Windows: ___  Linux: ___
- [ ] codex pane STAYS ALIVE (does not auto-terminate; the Linux symptom).  Win: ___  Linux: ___

### Step C — claude regression
- [ ] claude teammate still submits on Enter alone (no regression).  Windows: ___  Linux: ___

### Finalize (after both platforms)
- [ ] Set `cli_registry.py` codex `teammate_submit_keys` default to the WINDOWS winner.
- [ ] If Linux differs, it runs via `AGENT_TEAM_SUBMIT_KEYS_CODEX` until S13 adds
      `sys.platform` defaulting (see `docs/s13-next-phase-roadmap.md`).

## D12 — codex non-interactive
- [ ] Spawn a codex teammate; confirm it runs commands WITHOUT prompting for
      per-command approval and WITHOUT the first-run trust prompt (launched with
      --dangerously-bypass-approvals-and-sandbox).
- [ ] Confirm the lead never saw/issued any codex flag (decoupling invariant).
