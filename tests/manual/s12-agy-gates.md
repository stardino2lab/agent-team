# S12 agy (Antigravity) verification gates — run on THIS Windows box

Reproduce live, not inferred from docs. G0 + G1 + helper gate S12a (teammate).
Lead gates are deferred until the MCP spike (agy has no `mcp` subcommand).
agy 1.0.10.

## Free checks (no tokens) — G0 [DONE 2026-06-19]
- [x] `agy --version` → prints 1.0.10, exit 0. Launches from a non-TTY psmux pane.
- [x] `agy --help` shows `--dangerously-skip-permissions` (auto-approve all tools).
- [x] `agy --help` shows `-p/--print` + `--prompt-interactive` (headless vs interactive).
- [x] `agy help mcp` → "unknown subcommand: mcp" (confirms no MCP subcommand → lead deferred).

## Token / auth checks
- [ ] G1 (teammate): an INTERACTIVE `agy --dangerously-skip-permissions` pane accepts
      a kickoff via psmux send_keys and runs tool calls WITHOUT per-command approval
      or a first-run trust prompt. [token]
- [ ] Helper-under-agy (teammate): confirm the `agent-team` shell helper (mail/task/
      `teammate ready`) runs under agy on Windows (the teammate brief tells it to). [token]

## Deferred (lead — needs an MCP spike)
- [ ] Resolve how agy hosts an MCP server (Claude-Code `.mcp.json` project convention?
      `agy plugin import claude`? a config file under `~/.antigravity/`?). Only then can
      agy be evaluated as a lead. Out of scope for S12a.

## Outcome
- G0 (done) + G1 + helper PASS → S12a (agy teammate) is trustworthy to use.
- Lead is blocked on the MCP spike above.
