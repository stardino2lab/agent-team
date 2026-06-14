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

## D12 — codex non-interactive
- [ ] Spawn a codex teammate; confirm it runs commands WITHOUT prompting for
      per-command approval and WITHOUT the first-run trust prompt (launched with
      --dangerously-bypass-approvals-and-sandbox).
- [ ] Confirm the lead never saw/issued any codex flag (decoupling invariant).
