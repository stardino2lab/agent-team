# S9 — Claude lead manual gate

**Requires:** psmux 0.4.10+, Claude CLI logged in, `pip install -e .` through S8.

## Preconditions

- [ ] `psmux -V` works
- [ ] `claude --version` works
- [ ] S8 `agent-team start --dry-run` passed

## Steps

1. Open Windows Terminal, start psmux:
   ```powershell
   psmux new-session -s agent-team-s9
   ```

2. In pane 0, from a test project with `.agent-team/`:
   ```powershell
   cd c:\DEV\agent-team\tests\fixtures\minimal-project   # or payment-api when ready
   $env:AGENT_TEAM_SESSION_ID = "s9-test"
   agent-team start --no-dry-run
   ```

3. Verify MCP config points to `agent_team.mcp_server` (see `templates/claude-mcp.json.example`).

4. In lead pane, ask:
   ```
   List personas, then request spawning planner with prompt "Say hello in mail to lead"
   ```

5. In TUI approval modal:
   - [ ] Shows persona `planner`, CLI `claude`
   - [ ] Approve spawn

6. Verify:
   - [ ] New psmux pane or in-process teammate appears
   - [ ] `~/.agent-team/sessions/s9-test/events.jsonl` has `spawn_requested`, `spawn_approved`, `teammate_ready`
   - [ ] Mailbox message from planner in TUI Mail tab

7. Ask lead to shutdown teammate.

8. Record pass/fail in PROGRESS.md.

## Pass criteria

- One spawn approved via TUI
- events.jsonl audit trail complete
- No unhandled errors in TUI or lead pane
