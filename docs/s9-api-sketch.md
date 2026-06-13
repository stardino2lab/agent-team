# S9 API Sketch — Claude lead + real teammate

Review input for 5-expert gate. Implementation follows after BLOCKING=0.

## Design decisions

| Item | Decision |
|------|----------|
| Lead pane bootstrap | `agent-team start` creates the lead pane (s8 already did `new_session`) and `send_keys` a single command line that starts `claude` with both MCP config and system prompt baked in. No post-startup send_keys race. |
| MCP config file | Rendered per session at `{session_dir}/claude-mcp.json`. Static env interpolation done by agent-team (no `${VAR}` placeholders on disk). |
| MCP global isolation | `claude --strict-mcp-config` so the user's existing global servers (Drive/Gmail/Calendar/etc) are not loaded into the lead. |
| Lead context injection | `claude --append-system-prompt "<build_lead_context().text>"`. If the text exceeds the cmd line cap (8191 chars) or `--append-system-prompt-file` exists, switch to the file variant. |
| Teammate context | `TeammateRunner.spawn` renders `{session_dir}/teammates/{name}/AGENTS.md` from a bundled template, sets the teammate pane's cwd to that directory, then send_keys the persona prompt. |
| `teammate_ready` timing | Same as s8 — emitted immediately after `send_keys`. Real handshake (teammate writes a ready marker) deferred to S10+. The s9 manual checklist only requires the event entry, not a real reply round-trip. |
| Template location | Move `templates/claude-mcp.json.example` and `templates/teammate/AGENTS.md.codex.j2` from the repo root into `src/agent_team/bundled/templates/{lead,teammate}/` so they ship with `pip install -e .`. Drop the `.example` suffix and the codex-specific naming (one template per persona role, not per CLI). |
| Template rendering helper | New `agent_team.bundled_paths.render_bundled_template(rel_path, **vars) -> str`. Replaces the `_jinja_env()` duplicate in `cli/init.py`. |
| psmux session ownership | `agent-team start` creates the psmux session (same as s8). The user runs the command from outside psmux and later does `psmux attach -t SID` to see the panes. The s9 manual checklist text "in pane 0" is corrected. |
| Test slots | 4 unit (mcp render, lead send_keys, lead context, teammate AGENTS.md render) + 1 e2e (PsmuxBackend monkeypatch records the start sequence) + 1 minimal-project fixture. Manual smoke is the acceptance gate. |
| `--no-dry-run` flag | **Does not exist.** Default mode is real; `--dry-run` is the opt-in. The s9 manual checklist is updated accordingly. |

## Lead launch

```cmd
claude ^
  --mcp-config {session_dir}\claude-mcp.json ^
  --strict-mcp-config ^
  --append-system-prompt "<build_lead_context.text>"
```

Sent as a single line via `psmux.send_keys(lead_pane, cmd, enter=True)`. `PsmuxBackend.send_keys` already runs psmux with `shell=False`, so backslashes, quotes, and spaces in the argv are not re-interpreted. The only caller-side concern is escaping any double-quote inside the system-prompt text itself; `build_lead_context().text` is markdown without embedded quote sequences, so a single outer `"` pair suffices. If `--append-system-prompt-file` is available at install time, the implementation switches to the file variant unconditionally.

## MCP config render

Source template (moved to `src/agent_team/bundled/templates/lead/claude-mcp.json.j2`):

```jinja
{
  "mcpServers": {
    "agent-team": {
      "command": "python",
      "args": ["-m", "agent_team.mcp_server"],
      "env": {
        "AGENT_TEAM_HOME": "{{ agent_team_home }}",
        "AGENT_TEAM_SESSION_ID": "{{ session_id }}",
        "AGENT_TEAM_PROJECT_PATH": "{{ project_path }}"
      }
    }
  }
}
```

Rendered with the absolute, normalized forms of the three env paths at `Orchestrator.start` time. Written to `{session_dir}/claude-mcp.json`.

## Teammate AGENTS.md render

Source template (moved to `src/agent_team/bundled/templates/teammate/AGENTS.md.j2`):

```jinja
# {{ teammate_name }} ({{ persona }})

Session: {{ session_id }}
Lead: lead
CLI: {{ cli }}

You coordinate via:
- `agent-team mail send --session {{ session_id }} --as {{ teammate_name }} --to lead --body "..."`
- `agent-team mail read --session {{ session_id }} --as {{ teammate_name }} --since last`
- `agent-team task list --session {{ session_id }}`

Persona prompt:
{{ spawn_prompt }}
```

`TeammateRunner.spawn` renders to `{session_dir}/teammates/{teammate_name}/AGENTS.md` and calls `psmux.split_pane(... cwd={session_dir}/teammates/{teammate_name})`. The teammate's CLI (claude or codex) auto-reads AGENTS.md from the working directory (project convention). The `send_keys` payload then becomes just the persona spawn prompt — the rich coordination context is already on disk.

## Orchestrator.start sequence (updated)

```
1. SessionStore.create(...)
2. write claude-mcp.json   (new)
3. psmux.new_session(SID, cwd=project_path) → lead_pane   (s8 same)
4. psmux.send_keys(lead_pane, claude_launch_cmd, enter=True)   (new)
5. psmux.split_pane(SID, command="agent-team tui --session SID")   (s8 same)
6. event_log session_started
7. run_once + start_watching   (s8 same)
```

`--no-psmux` short-circuits steps 2-5 (file-only mode, unchanged).
`--dry-run` swaps `TeammateRunner` to mock but `start()` still does steps 2-4 (the lead pane in dry-run mode runs a real claude, but no real teammates spawn). If the manual checklist wants to skip even the lead launch, the existing `--no-psmux` already covers it.

## TeammateRunner.spawn sequence (updated)

```
1. teammate_dir = session_dir / "teammates" / teammate_name
2. teammate_dir.mkdir(parents=True, exist_ok=True)
3. write AGENTS.md from template
4. pane_id = psmux.split_pane(session, command=persona.cli, cwd=teammate_dir)
5. psmux.send_keys(pane_id, persona.spawn_prompt_template, enter=True)
6. return SpawnResult(pane_id, teammate_name, persona, cli, started_at)
```

The mock branch keeps recording (`recorded_spawns`) and skips steps 3-5.

## Event types

No new event types in S9. `session_started`, `teammate_ready`, `error`, `orchestrator_stopped` cover the manual checklist. Real handshake events (`teammate_replied`, etc.) belong to S10+.

## Test slots (S9)

| # | File | Verifies |
|---|------|----------|
| 1 | `tests/unit/test_orchestrator.py::test_start_writes_mcp_config_to_session_dir` | `{session_dir}/claude-mcp.json` exists with absolute paths and the session id |
| 2 | `tests/unit/test_orchestrator.py::test_start_sends_claude_launch_to_lead_pane` | `psmux.recorded_calls` contains `send-keys -t <lead_pane> -l "claude --mcp-config ... --strict-mcp-config --append-system-prompt ..."` |
| 3 | `tests/unit/test_orchestrator.py::test_start_appended_system_prompt_includes_lead_context` | the appended prompt contains a known substring from the minimal-project TEAM.md |
| 4 | `tests/unit/test_teammate_runner.py::test_spawn_renders_agents_md` | `{session_dir}/teammates/helper-1/AGENTS.md` exists and mentions persona, teammate name, session id |
| 5 | `tests/unit/test_cli_start_attach.py::test_start_real_mode_renders_mcp_and_sends_claude` | CliRunner + monkeypatched PsmuxBackend → all of #1-#3 from the CLI path |
| 6 | `tests/fixtures/minimal-project/` | new fixture: `.agent-team/config.yaml` + `TEAM.md`. Replaces the dynamic `consumer_project` for s9 tests |

Existing s8 tests keep passing — no regressions in dry-run paths.

## Reused utilities

- `agent_team.project_loader.ProjectLoader.build_lead_context()` (now actually called)
- `agent_team.psmux_backend.PsmuxBackend.{new_session, split_pane, send_keys}`
- `agent_team.event_log.EventLog.append`
- `agent_team.bundled_paths` package (extend with `render_bundled_template`)
- `cli/init.py:_jinja_env` pattern (extracted into a shared helper, then `init.py` reuses it)
- Test fixtures: `psmux_backend(mock=True)`, `session_store`, `event_log`

## Out of scope (S10+)

- Real `teammate_ready` handshake via marker file or first mailbox reply
- `Orchestrator.shutdown` (kill panes + archive)
- `EventLog.tail_by_type` API (s8 review carried this forward but `reconcile_handled` still works on full read for now)
- Multi-lead or shared psmux session across multiple agent-team sessions
- Codex-specific AGENTS.md sections (one template covers both for now)
- payment-api E2E — that's S10
