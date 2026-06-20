# S14a `agent-team status` health verification gates — run on THIS Windows box

The pure health derivation is unit-tested (test_health.py, every state + precedence).
These gates cover the two signals unit tests CANNOT model: a real crashed pane, and
whether the transcript mtime advances during silent work. Reproduce live.

## Free checks (no tokens)
- [ ] `agent-team status --session <id> --json` on a running session prints valid JSON
      with `members[]`, `task_counts`, `panes_available: true`, `overall_ok`.
- [ ] `agent-team status --session <id> --no-panes` sets `panes_available: false` and
      reports running members as `unknown` (never `dead`), `overall_ok` still true.
- [ ] `agent-team status --session <bad-id>` exits 1 (command error); a session with a
      member in `error`/`dead` exits 2 (unhealthy); a healthy session exits 0.

## Live checks (need a real psmux session; no tokens beyond a normal start)
- [ ] G-status-dead: start a session, then kill a teammate's pane directly
      (`psmux kill-pane -t %N` for that member's pane_id). Re-run `agent-team status` →
      that member shows `DEAD`, `overall_ok=false`, exit 2. The LEAD pane killed the same
      way must also read `DEAD` (lead has pane_id + status=running, so dead-detection
      applies — see test_build_health_dead_lead_makes_unhealthy).
- [ ] G-status-stale-falsepos: spawn a teammate and give it a LONG SILENT task (e.g. a
      multi-minute build/test that prints nothing). While it runs, confirm
      `teammates/<name>/transcript.log` MTIME ADVANCES (pipe_pane's `cat >>` is flushing)
      so a busy teammate does NOT read as `STALE`. If mtime stalls during silent work →
      false `stale`; remedy = lower-buffer the pipe or add an explicit heartbeat (note it
      here and feed S14c). Watched value: stale_after default = 600s.
- [ ] G-status-stale-truepos: leave a teammate idle (no output, no mail) past stale_after
      and confirm it reads `STALE` (advisory only — S14c decides escalation).

## Notes / limitations (by design in S14a)
- A teammate that CRASHES DURING STARTUP (before writing its `ready` marker) stays
  `starting` forever (poll_ready only flips starting→running on the marker). S14a shows
  `starting`, not `dead`/`stale`; detecting stuck-starting is deferred to S14c escalation.
- `stale` is advisory (activity-derived); `dead` (pane absent) is the only authoritative
  liveness verdict. Control-plane failures (psmux session gone, exe missing) →
  `panes_available=false`, never invented deadness.

## Outcome
- Free + G-status-dead + transcript-mtime PASS → `agent-team status` is trustworthy as
  the S14b/S14c/S18 observability + debug tool.
