# S10b — real teammate_ready handshake (design)

**Date:** 2026-06-15
**Status:** approved-by-default (autonomous S10 drive) — see PROGRESS S10 note
**Scope:** second slice of S10. Replace the fake `teammate_ready` (emitted right
after send_keys) with a real handshake: the teammate signals readiness and the
orchestrator emits `teammate_ready` only then.

## Problem

`Orchestrator._spawn_one` emits `teammate_ready` immediately after
`runner.spawn` + `update_members`, before the teammate CLI has booted or read
its brief. Downstream consumers (TUI, reconcile, future automation) cannot
trust the event to mean "the teammate is actually working".

## Approach — marker file + teammates-dir watcher (non-blocking)

1. **Ready marker.** The teammate, after reading its brief, runs a new
   CLI-neutral command that writes a marker file:
   `agent-team teammate ready --session <id> --as <name>` →
   `{session_dir}/teammates/{name}/ready` (JSON: `{"name", "ts"}`).
2. **Two-phase member status.** `_spawn_one` adds the member with
   `status="starting"` and records the originating `request_id` on the member;
   it no longer emits `teammate_ready`.
3. **poll_ready().** A new orchestrator method scans `starting` teammate members;
   for each whose `ready` marker exists, it flips status to `running`, saves, and
   emits `teammate_ready` (with `request_id`, `persona`, `name`, `pane_id`,
   `cli`). Idempotent: a member already `running` is skipped (no double-emit).
4. **Detection.** `start_watching` adds a recursive `FileWatcher` on
   `{session_dir}/teammates` that calls `poll_ready`; `run_once` and `attach`
   also call `poll_ready` so markers written while detached are reconciled.

No blocking wait in the spawn path; the approval-drain loop is never stalled
waiting for a teammate.

### Why not the alternatives

- **Blocking bounded wait inside `_spawn_one`** — stalls the approval watcher
  thread for up to the timeout per spawn. Rejected.
- **First-mailbox-reply as the ready signal** — conflates "ready" with "has
  something to say"; reuses mailbox but is semantically muddier. Rejected; the
  explicit marker is cleaner. (The api-sketch lists both options.)

## Data model

- `Member` gains `request_id: str | None = None` (persisted in session.json,
  backward-compatible default). Lets `poll_ready` emit `teammate_ready` with the
  originating request id after a detach/attach restart, without re-deriving it
  from resolutions (where `teammate_name` is often None).

## CLI

New `agent-team teammate ready --session <id> --as <name>`:
- `resolve_session_dir(session)` → `{session_dir}/teammates/{name}/ready`
- `safe_segment(name, "teammate")` before path use.
- Writes the marker via `write_json` (atomic). Idempotent (re-running is a no-op
  overwrite). Prints the marker path.
- The orchestrator — not this command — emits the `teammate_ready` event, so the
  event log stays single-writer.

## Brief template

Add to `teammate/AGENTS.md.j2`, before the task work, a startup step:

```
## When you are ready
Run this once after reading this brief, before starting work:

    agent-team teammate ready --session {{ session_id }} --as {{ teammate_name }}
```

The kickoff (`_kickoff_line`) already says "read your brief … then begin"; the
brief now tells the teammate to signal ready first.

## TUI

- `tui/loaders.py` / Team panel: show member `status` so `starting` vs `running`
  is visible (the handshake's observable effect besides the deferred event).
- No new event type: the absence of `teammate_ready` until the marker appears,
  plus the member status, is the signal. (Avoids churn in the event loaders.)

## Orchestrator changes

- `_spawn_one`: member `status="starting"`, `request_id=res.request_id`; drop the
  immediate `teammate_ready` emit.
- `poll_ready()`: reload session, for each `role=="teammate" and status=="starting"`
  member, if `{session_dir}/teammates/{name}/ready` exists → set `running`, save,
  emit `teammate_ready`.
- `start_watching`: `mkdir` the teammates dir; add `FileWatcher(teammates_dir,
  poll_ready, recursive=True)`; stop it in `stop_watching`.
- `run_once` and `attach`: call `poll_ready` after draining approvals.
- `reconcile_handled`: unchanged — a teammate already in `members` (even
  `starting`) counts as handled, so no re-spawn; ready ones are also covered by
  the existing `ready_request_ids` set from emitted `teammate_ready` events.

## Error handling / edge cases

- **Teammate never signals**: stays `starting`; visible in the TUI Team panel.
  No timeout/auto-degrade in S10b (deferred). Documented, not a hang (the
  orchestrator never blocks on it).
- **Idempotency / double fire**: `poll_ready` re-reads status and only acts on
  `starting` members; the flip-to-`running`+save before emit prevents a second
  emit on a rapid second watcher tick.
- **Marker race (written before watch starts)**: covered by `poll_ready` in
  `attach`/`run_once` and the watcher catching subsequent changes.
- **mock / no_psmux**: `_spawn_one` with `no_psmux` has no pane; still goes
  `starting` → the marker can be written (tests) → `running`. (mock teammates in
  dry-run won't write a marker; acceptable — dry-run doesn't assert readiness.)

## Testing

Unit:
- `_spawn_one` adds a `starting` member with `request_id` and emits **no**
  `teammate_ready`.
- `poll_ready` with the marker present → member `running` + one `teammate_ready`
  event with the right payload; without the marker → no change.
- `poll_ready` is idempotent (second call emits nothing more).
- new CLI writes the marker at the expected path; `safe_segment` rejects bad
  names.
- `Member` round-trips `request_id` through session.json.

## Acceptance

Unit green. Real end-to-end readiness is exercised by the S10d manual E2E.

## Out of scope

- Ready timeout / auto-degrade to `running` after N seconds.
- `teammate_spawning` event type / richer lifecycle states.
- Heartbeat / liveness beyond the one-shot ready marker.

## References

- `docs/RGIO.md` (TeammateRunner / Orchestrator contracts)
- `docs/s9-api-sketch.md` (handshake listed out-of-scope for S9)
- `docs/superpowers/specs/2026-06-14-s10a-teammate-work-foundation-design.md`
