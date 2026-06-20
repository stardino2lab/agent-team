# S11c manual checklist — codex as lead (D1–D4)

Run on the Windows box with real codex (0.139.0) + psmux. Unit tests cover the
launch-line/profile construction; these confirm codex actually leads.

> ## RESULT — 2026-06-20 Windows live run: **FAIL (codex lead does not get the MCP)**
> codex **0.141.0**, gpt-5.5, autonomous `codex exec`. Run on an isolated
> AGENT_TEAM_HOME + a `lead_cli: codex` copy of the payment-api fixture, session `cdx1`.
>
> What WORKED:
> - Profile written: `{CODEX_HOME}/agent-team-cdx1.config.toml` with `[mcp_servers.agent-team]`
>   + env (HOME/SESSION/PROJECT), valid TOML (D2 render OK).
> - Launch line clean (no shell-quoting breakage): `codex exec --ignore-user-config
>   --skip-git-repo-check --profile agent-team-cdx1 -C "<lead dir>" -o "<last>" "<bootstrap>"`.
> - codex read the working-root `AGENTS.md` and adopted the orchestration-only role
>   ("Operating as lead only: no direct code reads/edits… delegate through agent-team
>   tools only"). So D1/D3/D6 wiring is fine.
>
> What FAILED (the load-bearing unknown):
> - **codex never loaded the agent-team MCP server.** It said verbatim: *"I don't have
>   the exact `spawn_teammate`/mail tools exposed; the available surface is `spawn_agent`,
>   `send_input`, `wait_agent`, `close_agent`."* Those are codex's BUILT-IN `collab`
>   sub-agent tools, NOT our MCP. codex used `SpawnAgent`/`Wait`/`CloseAgent` to spawn a
>   codex-internal "explorer", declared "Ready for the milestone", and EXITED (28,479
>   tokens). `events.jsonl` = `session_started` ONLY — zero agent-team orchestration
>   (no `spawn_requested`, no MCP tool call).
>
> Likely cause: codex 0.141.0 does not load `[mcp_servers.*]` from a `--profile` OVERLAY
> file (MCP servers come from the BASE `~/.codex/config.toml` / `codex mcp add`), and/or
> `--ignore-user-config` strips it. Either way the "MCP-in-profile + --ignore-user-config"
> delivery does NOT expose the server to `codex exec`.
>
> Fallback candidates (need a spike — flagged as a follow-up):
> 1. **Inline `-c` MCP config** on the launch line — `-c 'mcp_servers.agent-team.command=…'
>    -c 'mcp_servers.agent-team.args=[…]' -c 'mcp_servers.agent-team.env.…=…'`. The `-c`
>    override mechanism is proven to work on this box (the update-nag fix uses
>    `-c check_for_update_on_startup=false`). Keeps session isolation. Needs careful
>    nested-key + env-map TOML encoding and a check that codex loads MCP from `-c`.
> 2. `codex mcp add agent-team …` into the BASE config (global, not session-isolated;
>    conflicts with `--ignore-user-config`).
> 3. Drop `--ignore-user-config` and put the server in base config (loses isolation).
>
> **Bottom line:** S11c codex-as-lead is NOT usable as implemented. claude lead works
> (verified same day). Keep `lead_cli: claude`; treat codex-lead as blocked on the
> MCP-delivery spike above.

> ## FIX — 2026-06-20: MCP now delivered inline via `-c` (not a `--profile` overlay)
> Root cause confirmed against codex **0.141.0**: codex does NOT load `[mcp_servers.*]`
> from a `--profile` overlay file — MCP servers are read only from the base config or
> from `-c` inline overrides. The launch line now drops `--profile` + the CODEX_HOME
> profile file entirely and injects the server via `-c`:
> ```
> codex exec --ignore-user-config --skip-git-repo-check \
>   -c "mcp_servers.agent-team.command='<python.exe>'" \
>   -c "mcp_servers.agent-team.args=['-m','agent_team.mcp_server']" \
>   -c "mcp_servers.agent-team.env.AGENT_TEAM_HOME='<home>'" \
>   -c "mcp_servers.agent-team.env.AGENT_TEAM_SESSION_ID='<sid>'" \
>   -c "mcp_servers.agent-team.env.AGENT_TEAM_PROJECT_PATH='<proj>'" \
>   -C "<lead dir>" -o "<last>" "<bootstrap>"
> ```
> Encoding: each value is a TOML **literal** string (single-quoted) so Windows
> backslashes survive verbatim and never collide with the shell double-quote wrap;
> `args` is a TOML array of literal strings. `--ignore-user-config` is KEPT — `-c`
> composes with it, so the lead sees ONLY agent-team (the user's base-config servers,
> e.g. `node_repl`, are stripped) and `~/.codex` is never mutated.
>
> Verified live on Windows (codex 0.141.0, psmux PowerShell pane):
> - `codex mcp list --json -c …` registers `agent-team` (empty CODEX_HOME → only
>   agent-team, proving `-c` survives `--ignore-user-config`).
> - The exact flags emitted by `_codex_mcp_c_flags` parse correctly in codex
>   (command/args/all 3 env vars intact), both via subprocess and through a REAL
>   psmux pane (`codex mcp get agent-team` shows it with the right command/args/env).
> - Code path: `_build_lead_launch_command` codex arm + `_codex_mcp_c_flags`
>   (unit-tested); no `.config.toml` is written to CODEX_HOME anymore.
> - PENDING below: full `codex exec` lead run calling `spawn_teammate` → `spawn_requested`.

## Setup
- [ ] In a fixture project's `.agent-team/config.yaml`, set `lead_cli: codex`.
- [ ] `agent-team start --session s11c --project <fixture>`.

## Inline `-c` MCP delivery + isolation
- [ ] Confirm NO `{CODEX_HOME}/agent-team-*.config.toml` is written (MCP rides the
      launch line; `~/.codex` is untouched).
- [ ] Confirm the launch line carries `-c "mcp_servers.agent-team.command=…"` (+ args
      + the 3 env vars) and NO `--profile`.
- [ ] Confirm codex exec under `--ignore-user-config` LOADS the `-c` server and the
      lead sees only agent-team (no `node_repl` / other base-config servers).

## Lead behaves
- [ ] The codex lead pane launches (no shell-quoting breakage of the command line).
- [ ] codex connects to the agent-team MCP server and can call a tool
      (e.g. list_personas / spawn_teammate round-trip → a `spawn_requested` event).
- [ ] codex reads `{session_dir}/lead/AGENTS.md` (the D6 preamble) and orchestrates
      per it — delegates coding, does not edit project files itself.
- [ ] Autonomous mode: codex exec drives spawn/mail/wait via MCP and exits when
      done; user approvals go through the TUI queue.

## Cleanup
- [ ] Nothing leftover in `{CODEX_HOME}` (no profile file is written anymore). The
      session_dir is the only artifact, cleaned on partial-start failure.

## Cost dial
- [ ] Flip `lead_cli` back to `claude` → next start launches the claude lead with
      no code change (revert = one-line config).
