# S12b — Gemini as lead (D5 full): Implementation Plan ⚠️ GATED / PLAN-ONLY

> **⚠️ DO NOT IMPLEMENT YET.** This sub-stage is **plan-only** by user decision. Landing gemini-as-lead code requires the **G0–G6 gates** (`tests/manual/s12-gemini-gates.md`) to PASS on the Windows box first — they are live (token-spending + interactive auth) and cannot be run in this session. An unverified gemini MCP-lead launch builder would be a *dead/broken spawn path* (D5). When all G0–G6 pass, finalize the live-unknown details flagged below, then execute this plan via superpowers:subagent-driven-development.

**Goal (when ungated):** Make `gemini` a launchable lead CLI — flip `config.yaml: lead_cli: gemini` and the orchestrator builds a real gemini lead pane that connects to the agent-team MCP server — completing the cost dial (any verified lead × any verified teammate).

**Architecture:** The S11c seam already generalized lead launch to per-CLI dispatch (`_build_lead_launch_command` elif chain + `_write_lead_mcp_config` format dispatch + `CliSpec.mcp_format`). S12b is a **drop-in third arm**: register gemini `supports_lead=True` with a gemini MCP format, add a gemini `elif` to both dispatch functions, and deliver the lead system prompt via a working-root `GEMINI.md` (gemini has no `--append-system-prompt-file`, same constraint codex had → same solution shape). Reference spec: `docs/s11-multi-cli-plan.md` (D5, S12b, D1/D2/D3 as the template).

**Tech Stack:** Python 3.12, pytest, ruff, `tomllib`/json. psmux mocked. The live gemini-lead E2E (profile/MCP load, isolation, GEMINI.md application, long-run, failure semantics) = G2–G6 in `tests/manual/`.

---

## Verified gemini facts (gemini 0.46.0, non-token probes on this box)

- **MCP registration:** `gemini mcp add <name> <commandOrUrl> [args...]` with `-s project|user` (default `project`), `-t stdio`, `-e KEY=value` (repeatable), `--trust` (bypass tool-call confirmation for that server), `--description`. `-s project` writes to a **project-scoped** `.gemini/` config under the cwd; `-s user` → `~/.gemini/`.
- **MCP isolation:** `--allowed-mcp-server-names <name>` (array) whitelists servers for a launch — gemini's `--strict-mcp-config`/`--ignore-user-config` analog (only the named server(s) load).
- **System prompt:** no `--append-system-prompt-file`. gemini reads `GEMINI.md` from its working root (the `AGENTS.md`/`CLAUDE.md` analog). Working root extendable via `--include-directories`.
- **Headless vs interactive:** `-p/--prompt` = headless single-shot (autonomous, exits); default = interactive REPL. `--approval-mode yolo` / `-y` auto-approve; `--skip-trust` skip workspace trust.

## Live unknowns to resolve via the G-gates BEFORE finalizing code

1. **(G2) The exact `.gemini` project-config file** that `gemini mcp add -s project` writes (path + JSON shape) — so `_write_lead_mcp_config` can render it directly into a session-scoped working root instead of mutating the project. Candidate: `{lead_dir}/.gemini/settings.json`. **Discover by running `gemini mcp add -s project … agent-team …` in a throwaway dir and inspecting the file.**
2. **(G2/G3) Does `--allowed-mcp-server-names agent-team` + a session-scoped `{lead_dir}/.gemini/` config actually load ONLY our server** (isolation), with the lead pane cwd = `{lead_dir}`? Or is a `gemini mcp add` registration (which writes config) required vs. a hand-written settings file?
3. **(G4) Does gemini apply `{lead_dir}/GEMINI.md`** as the lead system prompt when cwd/working-root = `{lead_dir}`? (probe with a required output token.)
4. **Lead interaction mode:** interactive `gemini` + send_keys bootstrap (claude-like, user can interject) vs. `gemini -p "<bootstrap>"` autonomous (codex-exec-like). **Recommend interactive** (the lead pane is send_keys-driven like claude; the user retains TUI + pane interjection), but confirm gemini interactive + MCP + `--approval-mode yolo` holds over a long session (G5).

Until 1–4 are answered live, the code below is a **sketch** — the registry `mcp_format` value, the `_write_lead_mcp_config` gemini renderer, and the launch line may need adjustment.

---

## Planned File Structure (when ungated)

- Modify: `src/agent_team/cli_registry.py` — flip gemini `supports_lead=True`; add `mcp_format="gemini"` (a new format; the `.gemini` settings JSON differs from claude's `--mcp-config` JSON shape). Keep `teammate_launch_args` from S12a.
- Modify: `src/agent_team/orchestrator.py` — `_write_lead_mcp_config` gemini branch (render the `.gemini` settings into `{lead_dir}/.gemini/`); `_build_lead_launch_command` gemini elif; `start()` already format-aware (the toml/else branch becomes a 3-way or the gemini branch slots in); `_write_gemini_lead_context` (GEMINI.md). Partial-start cleanup (the `.gemini` dir is under session_dir → already covered by `rmtree(session_dir)`, unlike the codex CODEX_HOME profile — note this simplification).
- Test: `tests/unit/test_cli_registry.py`, `tests/unit/test_orchestrator.py`.
- New: `tests/manual/s12b-gemini-lead.md`.

---

## Task sketch (TDD, to execute AFTER G0–G6 pass)

### Task 1: registry — gemini lead-capable
- Test: `test_gemini_is_lead_capable` — `supports_lead=True`, `mcp_format=="gemini"`, `is_lead_supported("gemini")` True.
- Impl: flip gemini `supports_lead=True`, `mcp_format="gemini"`. The post-S11c invariant requires `mcp_format` for leads (satisfied); `mcp_format=="gemini"` (not "json") so no `mcp_config_filename` required — keep it `None` (gemini config lives in the working-root `.gemini/`, derived, not a session-root filename).
- **Confirm** `test_spec_invariant` still passes with the new gemini format. May need to extend the invariant to allow `mcp_format in {"json","toml","gemini"}` if a whitelist is added (currently it only special-cases "json").

### Task 2: `_write_lead_mcp_config` gemini branch (MUST add this arm, else runtime raise)
- The S11c `_write_lead_mcp_config` dispatches `json`/`toml` then raises `LeadCliNotSupportedError` for any other format. A gemini `elif spec.mcp_format == "gemini"` arm is REQUIRED or a gemini lead start raises before reaching the launch builder.
- Test: `test_write_lead_mcp_config_gemini_renders_dot_gemini_settings` — with cwd/lead_dir under tmp, the gemini branch writes `{lead_dir}/.gemini/settings.json` containing the agent-team stdio server (command=`sys.executable`, args, env: SESSION_ID/PROJECT_PATH/HOME), and the file parses as JSON. **Candidate shape (verify in G2): `{"mcpServers": {"agent-team": {"command":…, "args":[…], "env":{…}}}}` — confirm the exact key (`mcpServers`?) + filename (`settings.json`?) by running `gemini mcp add -s project … agent-team …` in a throwaway dir and inspecting the written file.**
- Impl: render the discovered `.gemini/settings.json` into `{lead_dir}/.gemini/`. Reuse `_lead_mcp_server_config` (already shared from S11c). Because it lives under `session_dir/lead`, normal `rmtree(session_dir)` cleans it up — NO CODEX_HOME-style external cleanup needed (simpler than codex).

### Task 3: `_build_lead_launch_command` gemini elif + GEMINI.md
- Test: `test_build_lead_launch_command_for_gemini_includes_required_tokens` — line contains `gemini`, `--allowed-mcp-server-names agent-team`, `--approval-mode yolo`, `--skip-trust`, and (if interactive) a send_keys bootstrap OR (if headless) `-p "<bootstrap>"`; cwd = lead_dir; NOT the claude/codex flags.
- Impl: `_write_gemini_lead_context(session_dir, text)` → `{session_dir}/lead/GEMINI.md` (returns lead_dir). gemini elif builds the launch line (interactive recommended; flag the mode per live unknown #4). All tokens shell-safe (server NAME + double-quoted paths/bootstrap), like codex.

### Task 4: `start()` wiring (3-way format dispatch) + the 2 codex-style refusal tests
- The S11c `start()` branches `if mcp_format == "json" … else (toml)`. Convert the implicit `else` to an explicit `elif spec.mcp_format == "toml"` and add `elif spec.mcp_format == "gemini"` (write `.gemini/settings.json` + `GEMINI.md` + the gemini launch line, cwd = lead_dir). The implicit-else comment `# toml (codex)` becomes misleading in a 3-way — make it explicit.
- Test: `test_start_gemini_lead_writes_dot_gemini_and_sends_gemini` (config `lead_cli: gemini`, mock psmux): asserts `.gemini/` settings + `lead/GEMINI.md` (with the D6 preamble) written, send-keys payload has `gemini --allowed-mcp-server-names agent-team`.
- antigravity stays unregistered; the S11c "antigravity/gemini planned for S12+" defensive arm/gate message: with gemini now a lead, update to "(antigravity planned later)" and adjust the matching tests.

### Task 5: manual checklist + PROGRESS
- `tests/manual/s12b-gemini-lead.md`: the live G2–G6 lead checklist (MCP handshake → 11 tools; isolation; GEMINI.md applied; long-run; kill/restart). PROGRESS S12b entry. Mark agy permanently deferred (no MCP).

---

## Gate dependencies (why plan-only)

| Gate | Blocks | Why |
|------|--------|-----|
| G0 (binary + non-TTY pane launch) | all | the lead pane cannot launch without it. |
| G1 (headless/interactive launch returns + behaves) | all | the lead must run in the pane reliably. |
| G2 (MCP handshake, 11 tools; `.gemini` config mechanism) | Tasks 1–4 | Determines the `mcp_format` renderer shape + that gemini can be an MCP client at all. The load-bearing lead capability. |
| G3 (isolation) | Task 2/3 | Confirms `--allowed-mcp-server-names` + session-scoped `.gemini` isolates from user globals. |
| G4 (GEMINI.md applies) | Task 3 | The lead's D6 orchestration-only preamble must actually constrain gemini. |
| G5 (long-run) | ship | A lead is non-hot-swappable; a mid-session wedge derails the team. |
| G6 (failure semantics) | ship | Orchestrator must detect a dead gemini lead; no zombie pane. |

All G0–G6 PASS (reproduced live, not inferred) → finalize the live-unknown details → execute Tasks 1–5 → plan-review→impl→code-review→verify (the normal sub-stage workflow).

## agy (antigravity) — researched, deferred (not in S12)

`agy` 1.0.8 has **no `mcp` subcommand** and no MCP-client surface (its Managed Agent API is a different surface without MCP). A lead MUST be an MCP client (it calls `spawn_teammate`/`send_message`/`wait_for_event`), and even a teammate coordinates via the `agent-team` shell helper (which `agy` could run) but gains nothing without the cost story being verified. **Recommendation:** do NOT register `agy`; revisit only if `agy` adds MCP. Recorded here + in PROGRESS so it isn't silently dropped.

## Lower-priority note (from spec D5/S12b)

Even once gated-in, a gemini lead saves little (the lead is the *cheap* role) and bets the non-hot-swappable lead seat on the most fragile capability (MCP client on Windows headless). Do it only with a concrete reason (e.g. Claude quota genuinely binding the lead). The high-value gemini win is the **S12a teammate** (already landed) — heavy coding on the unlimited tier.

## Expert plan-review axes (run now, on THIS plan-only doc)

- **E1 Seam fit** — does S12b slot into the S11c per-CLI dispatch cleanly (registry `mcp_format`, the two dispatch functions, `start()` 3-way)? Is `mcp_format="gemini"` the right modeling, or reuse "json"?
- **E2 MCP/isolation mechanism** — is the `.gemini` session-scoped working-root config + `--allowed-mcp-server-names` approach sound and shell-safe? Are the live unknowns (file shape, isolation) correctly flagged as G-gated rather than guessed?
- **E3 System-prompt delivery** — GEMINI.md-in-working-root (codex-AGENTS.md analog); interactive-vs-headless lead-mode tradeoff surfaced?
- **E4 Gate discipline** — are the G2–G6 dependencies correct and is the plan honestly plan-only (no code landing) per D5 + the user decision?
- **E5 agy + scope** — agy correctly deferred with rationale; no scope creep; lower-priority caveat retained.
