# RGIO — Module Contracts

**Role / Goal / Input / Output** for each orchestrator module.  
Implementation must not violate these contracts. Details in [IMPLEMENTATION.md](IMPLEMENTATION.md).

## SessionStore

| | |
|---|---|
| **Role** | Persist session metadata and paths |
| **Goal** | Single session.json per run |
| **Input** | `session_id`, `project_path`, `psmux_session`, `members[]` |
| **Output** | `~/.agent-team/sessions/{id}/session.json` |

## Mailbox

| | |
|---|---|
| **Role** | Async message broker between agents |
| **Goal** | Deliver messages to recipient inbox JSONL |
| **Input** | `{session_id, from, to, body, timestamp?}` |
| **Output** | Append line to `{session}/mailbox/{to}.jsonl`; notify event log |

**Message line schema:**

```json
{"id":"uuid","from":"lead","to":"planner-1","body":"...","ts":"ISO8601"}
```

## TaskBoard

| | |
|---|---|
| **Role** | Shared work items with dependencies |
| **Goal** | CRUD + claim/complete with dep blocking |
| **Input** | task spec: `title`, `description`, `deps[]`, `assignee?` |
| **Output** | `{session}/tasks/{task-id}.json` state: `pending\|in_progress\|completed` |

## EventLog

| | |
|---|---|
| **Role** | Audit timeline |
| **Goal** | Append-only, TUI/web tail |
| **Input** | `{type, payload, ts}` |
| **Output** | `{session}/events.jsonl` one JSON per line |

## PsmuxBackend

| | |
|---|---|
| **Role** | tmux-compatible pane control |
| **Goal** | create/kill/send-keys/list panes |
| **Input** | session name, split direction, shell command |
| **Output** | `pane_id` (e.g. `%3`); errors if psmux missing |

## SpawnApproval

| | |
|---|---|
| **Role** | User gate for teammate spawn |
| **Goal** | pending → approved \| denied |
| **Input** | `{persona, cli, prompt_preview, requested_by}` |
| **Output** | `{session}/approval/pending.json` → resolved file or flag |

## McpServer

| | |
|---|---|
| **Role** | Expose orchestrator tools to Claude lead |
| **Goal** | 7 tools wired to modules above |
| **Input** | MCP tool calls |
| **Output** | JSON results + side effects (mailbox, tasks, approval queue) |

**Tools:** `list_personas`, `spawn_teammate`, `shutdown_teammate`, `send_message`, `read_messages`, `create_task`, `claim_task`, `complete_task`, `list_teammates`

## PersonaRegistry

| | |
|---|---|
| **Role** | Load YAML persona catalog |
| **Goal** | Merge global + project personas; enforce allowlist |
| **Input** | paths: `~/.agent-team/personas/`, `./.agent-team/personas/` |
| **Output** | `Persona` objects with `name`, `cli`, `spawn_prompt_template` |

## ProjectLoader

| | |
|---|---|
| **Role** | Load consumer project context |
| **Goal** | TEAM.md + config.yaml + playbook for lead prompt |
| **Input** | `cwd` project path |
| **Output** | `LeadContext` string + config dict |

## TeammateRunner

| | |
|---|---|
| **Role** | Start Claude or Codex in psmux pane |
| **Goal** | Inject role prompt + coordination instructions |
| **Input** | persona, name, session_id, pane_id |
| **Output** | Running CLI process; AGENTS.md fragment for Codex |

## Orchestrator

| | |
|---|---|
| **Role** | Session lifecycle |
| **Goal** | start / attach / dry-run / shutdown |
| **Input** | CLI args: `--playbook`, `--dry-run`, `--project` |
| **Output** | Active session; coordinates all modules |

## TextualTUI

| | |
|---|---|
| **Role** | Human observer + spawn approver |
| **Goal** | Mail, Tasks, Team, Log tabs + approval modal |
| **Input** | watchfiles on session dir |
| **Output** | User Y/N on spawn; live display |
