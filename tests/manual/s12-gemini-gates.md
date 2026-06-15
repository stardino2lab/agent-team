# S12 gemini verification gates (G0–G6) — run on THIS Windows box

Reproduce live, not inferred from docs. G0/G1 + auto-approve gate S12a (teammate);
G2–G6 gate S12b (lead). gemini 0.46.0.

## Free checks (no tokens)
- [ ] G0: `gemini --version` → prints version, exit 0. Launches from a non-TTY
      psmux pane (no TTY assumption).
- [ ] `gemini --help | Select-String "prompt"` shows `-p/--prompt` (headless).
- [ ] `gemini --help | Select-String "approval-mode"` shows yolo/auto_edit (D12-analog).
- [ ] `gemini mcp list` runs (MCP subcommand exists — lead-relevant).
- [ ] `gemini --help | Select-String "allowed-mcp-server-names"` (isolation flag, lead).

## Token / auth checks
- [ ] G1 (teammate): `gemini -p "say hi"` → returns output AND exits cleanly
      (no REPL/hang/keypress). [token]
- [ ] D12-analog (teammate): an INTERACTIVE `gemini --approval-mode yolo --skip-trust`
      pane accepts a kickoff via psmux send_keys and runs tool calls WITHOUT
      per-command approval or a trust prompt. [token]
- [ ] Helper-under-gemini (teammate): confirm `agent-team` shell helper (mail/task/
      `teammate ready`) runs under gemini on Windows (the teammate brief tells it to).
- [ ] G2 (lead): register `gemini mcp add agent-team python -m agent_team.mcp_server
      -e AGENT_TEAM_SESSION_ID=... -e AGENT_TEAM_PROJECT_PATH=...`; launch with
      `--allowed-mcp-server-names agent-team`; confirm handshake returns all 11 tools
      and one tool round-trips. [token]
- [ ] G3 (lead): with `--allowed-mcp-server-names agent-team`, only our server loads
      (no user global MCP bleed-through). [token]
- [ ] G4 (lead): a `GEMINI.md` in the working root is actually applied (probe with a
      required output token). [token]
- [ ] G5 (lead): survives a long pane (many turns, no auth expiry/wedge; degrades on
      quota). [token]
- [ ] G6 (lead): kill/timeout/restart — orchestrator detects a dead pane, no zombie. [mixed]

## Soft G7
- [ ] Primary-source confirmation that Windows + headless + (CLI) MCP is supported.

## Outcome
- G0/G1 + D12-analog PASS → S12a (gemini teammate) is trustworthy to use.
- ALL G0–G6 PASS → unblocks S12b (gemini lead) implementation.
