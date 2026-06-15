# S11c manual checklist — codex as lead (D1–D4)

Run on the Windows box with real codex (0.139.0) + psmux. Unit tests cover the
launch-line/profile construction; these confirm codex actually leads.

## Setup
- [ ] Check `{CODEX_HOME}/` has no pre-existing `agent-team-*.config.toml` profile
      that could collide (low risk — sid-scoped, agent-team is new).
- [ ] In a fixture project's `.agent-team/config.yaml`, set `lead_cli: codex`.
- [ ] `agent-team start --session s11c --project <fixture>`.

## Profile + isolation (the load-bearing live unknown)
- [ ] Confirm `{CODEX_HOME}/agent-team-s11c.config.toml` was written with
      `[mcp_servers.agent-team]`.
- [ ] Confirm `codex exec --ignore-user-config --profile agent-team-s11c` actually
      LOADS the profile's MCP server (i.e. --ignore-user-config does not also block
      the profile). If it does block it, note here and fall back (e.g. drop
      --ignore-user-config, or use inline -c): ____________________

## Lead behaves
- [ ] The codex lead pane launches (no shell-quoting breakage of the command line).
- [ ] codex connects to the agent-team MCP server and can call a tool
      (e.g. list_personas / spawn_teammate round-trip).
- [ ] codex reads `{session_dir}/lead/AGENTS.md` (the D6 preamble) and orchestrates
      per it — delegates coding, does not edit project files itself.
- [ ] Autonomous mode: codex exec drives spawn/mail/wait via MCP and exits when
      done; user approvals go through the TUI queue.

## Cleanup
- [ ] After the session, `{CODEX_HOME}/agent-team-s11c.config.toml` is leftover
      (graceful cleanup is the carried-backlog Orchestrator.shutdown item). Remove
      it manually for now if desired.

## Cost dial
- [ ] Flip `lead_cli` back to `claude` → next start launches the claude lead with
      no code change (revert = one-line config).
