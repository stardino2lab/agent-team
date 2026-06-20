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
- [ ] Spawn a codex teammate. Windows: no env needed (default Enter = Step-A winner).
      Linux: `set AGENT_TEAM_SUBMIT_KEYS_CODEX="Tab Enter"` first (Linux Step-A winner).
- [ ] Kickoff auto-SUBMITS — codex starts working (reads brief, runs `agent-team
      teammate ready`) with NO manual nudge.  Windows: ___  Linux: ___
- [ ] codex reaches `teammate_ready` + sends mail.  Windows: ___  Linux: ___
- [ ] codex pane STAYS ALIVE (does not auto-terminate; the Linux symptom).  Win: ___  Linux: ___

### Step C — claude regression
- [ ] claude teammate still submits on Enter alone (no regression).  Windows: ___  Linux: ___

### Finalize (after both platforms)
- [x] Set `cli_registry.py` codex `teammate_submit_keys` default to the WINDOWS winner
      = `("Enter",)` (codex override removed; uses the class default). Done 2026-06-20.
- [ ] Linux runs via `AGENT_TEAM_SUBMIT_KEYS_CODEX="Tab Enter"` until S13 adds
      `sys.platform` defaulting (see `docs/s13-next-phase-roadmap.md`). Re-confirm the
      Linux Step A/B on the env-override build (the prior Linux e2e predated it).

## D12 — codex non-interactive
- [ ] Spawn a codex teammate; confirm it runs commands WITHOUT prompting for
      per-command approval and WITHOUT the first-run trust prompt (launched with
      --dangerously-bypass-approvals-and-sandbox).
- [ ] Confirm the lead never saw/issued any codex flag (decoupling invariant).
