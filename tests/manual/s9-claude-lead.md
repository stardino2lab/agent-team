# S9 - Claude lead manual gate

**Requires:** psmux 0.4.10+, Claude CLI 2.x logged in, `pip install -e .` through S9.

## Preconditions

- [ ] `psmux -V` works
- [ ] `claude --version` works
- [ ] S8 `agent-team start --dry-run --no-psmux` smoke green
- [ ] Unit + e2e: `pytest tests/ -q` all green

## Steps

1. From any Windows shell (cmd or PowerShell) outside psmux, run:

   ```cmd
   cd <repo>\tests\fixtures\minimal-project
   agent-team start --project . --session s9-test
   ```

   - This shell becomes the orchestrator (do NOT close it; Ctrl-C stops the session).
   - A new psmux session `s9-test` is created in the background with two panes:
     - pane 0: lead - `claude --mcp-config ...\claude-mcp.json --strict-mcp-config --append-system-prompt "..."`
     - pane 1: TUI - `agent-team tui --session s9-test`

2. In a SECOND shell, attach to view the panes:

   ```cmd
   psmux attach -t s9-test
   ```

3. Verify the lead pane:

   - [ ] `claude` is running (interactive prompt visible)
   - [ ] In claude, ask `/mcp` (or equivalent) - the `agent-team` server lists.
         Globally registered servers (Drive/Gmail/Calendar) are NOT loaded
         (because of `--strict-mcp-config`).
   - [ ] System prompt mentions content from `tests/fixtures/minimal-project/TEAM.md`.

4. In the lead pane, ask:

   ```
   List personas (use the MCP tool), then request spawning planner with
   prompt "Send a hello mail to lead from planner."
   ```

5. In the TUI pane, the approval modal appears:

   - [ ] persona `planner`, cli `claude`, prompt preview visible
   - [ ] Press Y to approve

6. Verify in TUI:

   - [ ] Event Log shows `spawn_requested`, `spawn_approved`, `teammate_ready`
   - [ ] Team panel adds `helper-1 (teammate, claude, planner)`
   - [ ] Mailbox shows the planner -> lead message within a few seconds

7. Inspect on disk:

   - [ ] `%USERPROFILE%\.agent-team\sessions\s9-test\teammates\helper-1\AGENTS.md` exists
   - [ ] `%USERPROFILE%\.agent-team\sessions\s9-test\claude-mcp.json` has the
         session id baked in (no `${VAR}` placeholders)
   - [ ] `events.jsonl` contains the full lifecycle and an `orchestrator_stopped`
         line appears after Ctrl-C

8. Ctrl-C the orchestrator shell, then record pass/fail in `PROGRESS.md`.

## Pass criteria

- One spawn approved via TUI
- events.jsonl audit trail complete (`session_started` -> `spawn_*` -> `teammate_ready` -> `orchestrator_stopped`)
- No unhandled errors in TUI or lead pane
- `--strict-mcp-config` isolates the lead from the user's global MCP servers

## Known gotchas (S9 scope)

- The `teammate_ready` event fires the moment the orchestrator finishes
  `send_keys` to the new pane. It does NOT mean the LLM has actually
  finished booting. Real ready-handshake is S10+.
- `lead_cli` other than `claude` (e.g. `codex`, `antigravity`) raises
  `NotImplementedError` from `_build_lead_launch_command` - this is
  intentional in S9 and only switches on in S11+.
