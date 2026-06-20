# S18a external-approver gate — Hermes resolves spawns with no TUI

The CLI mechanism (`approvals list|approve|deny`, decided_by attribution, the
same resolution/event/cleared-pending state as a TUI approval) is unit-tested
(`test_cli_approve.py`). This gate verifies the end-to-end invariant on a real
session: a spawn requested by the lead is resolved by an EXTERNAL approver and
the teammate then spawns, with the TUI never opened.

## Steps (no second human; you play "Hermes")
- [ ] Start a session (`agent-team start --project <repo> --session <sid>`), or
      attach to one. Have the lead call `spawn_teammate` (or seed a pending via a
      lead pane). Confirm `agent-team status --session <sid>` shows
      `pending approval: apr-001 (...)`.
- [ ] `agent-team approvals list --session <sid> --json` → prints the pending
      request (`request_id`, `persona`, `cli`, `prompt_preview`, `requested_by`).
      Confirm the FULL prompt is NOT in the output.
- [ ] `agent-team approvals approve --session <sid> --id apr-001 --by hermes`
      → prints `approved apr-001 by hermes`.
- [ ] Confirm `approval/resolutions.jsonl` has the resolution with
      `decided_by: "hermes"` and `events.jsonl` has a `spawn_approved` event.
- [ ] Confirm the orchestrator then spawns the teammate (a new pane appears /
      `agent-team status` lists the teammate) — identical to a TUI approval, the
      TUI modal was never opened.
- [ ] Deny path: trigger another pending, run `approvals deny --session <sid>
      --id <apr> --by hermes` → `spawn_denied` event, no pane spawned.

## Error/edge checks (free, no spawn)
- [ ] `approvals approve` with no pending request → exits 1 with a clean message
      (no Python traceback).
- [ ] `approvals approve --id <wrong-apr>` → exits 1 (request-id mismatch).
- [ ] Double-approve (run approve twice) → second exits 1, and
      `resolutions.jsonl` has exactly ONE resolution (no duplicate).

## Notes / scope (S18a)
- The spawn gate is NOT removed — every spawn is still resolved by an approver;
  S18a only lets that approver be a program. `decided_by` records who.
- **Concurrency:** the cross-process `approve` is a writer-vs-reader race with the
  orchestrator (single writer of `resolutions.jsonl`; the reader tolerates torn
  lines), safe for S18a. A file lock on `approval/` is S18b/concurrency hardening.
- **Deferred:** `approvals list --watch` (use `logs tail --follow` on
  `spawn_requested` for now) and `config.yaml: approver: hermes` (TUI-modal
  suppression) are not in S18a.
- **CRITICAL:** approving with Hermes removes the last human who reads spawn
  intent, but per-teammate actions were already auto-approved by design. Real
  containment is S17 (worktree isolation) + sandboxed codex + agy-excluded/VM,
  NOT the spawn gate. Do not run an external-approver session without S17.

## Outcome
- External approve drives a spawn attributed `hermes`, deny blocks it, and the
  error paths exit 1 cleanly → the external-approver mechanism is trustworthy for
  the S18c headless E2E.
