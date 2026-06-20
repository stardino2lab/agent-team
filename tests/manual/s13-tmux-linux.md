# S13c — tmux backend live verification on Linux/macOS (G3/G4)

The TmuxBackend argv is unit-tested (test_tmux_backend.py) under the mock on the
Windows box, with NO real tmux. These gates verify the LIVE behavior that mocks
cannot model: a real tmux session, real pane I/O, and a real claude lead. Run on a
Linux host (G3); optionally macOS (G4).

## Preconditions
- [ ] `tmux -V` >= **3.4** (TmuxBackend uses `split-window -l N%`, which replaced
      `-p N` in 3.4). On tmux < 3.4 only cosmetic pane sizing breaks; note the
      version here: ____________
- [ ] `claude --version` resolves; `pip install -e .`; `pytest tests/ -q` green.
- [ ] Start from an **activated venv** so the tmux pane inherits the orchestrator's
      PATH/venv (the lead/teammate CLIs and `agent-team` helper must resolve in-pane).

## Free checks (no tokens)
- [ ] `AGENT_TEAM_BACKEND=tmux python -c "from agent_team.terminal_backend import
      make_terminal_backend as m; b=m(); print(b.name)"` prints `tmux` (real factory
      resolves the tmux binary — the one path the unit mock cannot cover).
- [ ] `agent-team status --session <id> --no-panes --json` works (backend-independent).

## Live checks
- [ ] G3-launch: `AGENT_TEAM_BACKEND=tmux agent-team start --project . --session s13c`
      then `tmux attach -t s13c`. The lead pane runs `claude`; the MCP server
      `agent-team` is listed under `--strict-mcp-config`; the appended system prompt
      content is present.
- [ ] G3-split-multipane: confirm the lead+TUI split worked (≥2 panes) AND that a
      THIRD pane (a teammate spawn) is created correctly. This exercises the
      pane-id discovery diff (`list_panes` after-before) on a session that ALREADY
      has multiple panes — the one inherited behavior most likely to break on real
      tmux vs the single-pane mock.
- [ ] G3-kickoff: approve one spawn; confirm the `-l`+Enter kickoff is actually
      SUBMITTED (teammate starts working — reads its brief, runs `agent-team teammate
      ready`), `teammate_ready` fires, and `teammates/<name>/transcript.log` is
      written by `pipe-pane` (the `cat >> "<path>"` redirect works in bash).
- [ ] G3-status-dead: kill the teammate's pane (`tmux kill-pane -t %N`); `agent-team
      status --session s13c` shows it `DEAD`, exit 2 (validates S14a dead-detection
      against a real tmux `list-panes`).
- [ ] G3-stop: Ctrl-C the orchestrator → `orchestrator_stopped` event; `tmux kill-
      session -t s13c` cleans up with no orphan panes.
- [ ] (G4, optional) Repeat G3-launch + G3-kickoff on macOS.

## Recommended (leave as a follow-up, not run here)
- [ ] Add a `ubuntu-latest` CI job running `pytest tests/ -q` with
      `AGENT_TEAM_BACKEND=tmux` under the mock (no real tmux needed) — the only
      recurring guard that a future edit doesn't silently re-break the tmux path.
      No .github/workflows exists yet; create one when CI is wanted.

## Notes
- Windows is unaffected: the factory still defaults to psmux on win32; tmux is
  selected only by platform default (POSIX) or `AGENT_TEAM_BACKEND=tmux`.
- Launch-line quoting is currently the Windows double-quote form; on POSIX
  `str(path)` is already forward-slash and double-quotes work in bash, so basic
  paths launch fine. Paths with spaces/special chars on POSIX would want
  `quote_pane_arg(..., shell_family="posix")` (shlex) — wire if a gate surfaces it.

## Outcome
- G3 (Linux launch + multipane split + kickoff + dead-detection + clean stop) PASS
  → the tmux backend is trustworthy; agent-team runs on Linux. Record in PROGRESS.md.
