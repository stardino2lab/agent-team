# IMPLEMENTATION — S0 through S10

Milestone spec for `c:\DEV\agent-team`.  
**Workflow:** implement → `pytest` / checklist → report → user approve → commit → (optional) push.

---

## P0 — Documentation (done)

**Deliverables:** PRD, RGIO, AGENTS.md, IMPLEMENTATION (this file), PROGRESS, README, `.gitignore`, `.cursor/rules/caveman.mdc`

**Verify:** agent guidance in [AGENTS.md](../AGENTS.md) + [docs/agents/](agents/); no `src/` yet.

**Commit:** `docs(p0): initial project documentation`

## P0.5 — Supplemental spec (done)

**Deliverables:** §Schemas/MCP/Dependencies in this file; architecture; project-integration; playbooks; personas; templates; manual S9/S10

**Verify:** all paths in [§Related docs](#related-docs) exist; no `src/` yet.

**Commit:** `docs(p0.5): schemas mcp playbooks personas and manual tests`

---

## S0 — Scaffold

**Files:**

```
pyproject.toml
src/agent_team/__init__.py
src/agent_team/__main__.py
tests/conftest.py
tests/unit/test_placeholder.py
```

**pyproject.toml:** name `agent-team`, python >=3.12, deps: `click`, `pyyaml` (minimal); dev: `pytest`, `ruff`

**Verify:**

```powershell
pip install -e c:\DEV\agent-team
pytest tests/ -q
agent-team --help   # optional stub
```

**Commit:** `feat(s0): project scaffold`

---

## S1 — Core data layer

**Files:**

- `src/agent_team/session.py`
- `src/agent_team/mailbox.py`
- `src/agent_team/tasks.py`
- `src/agent_team/event_log.py`
- `tests/unit/test_mailbox.py` (4+ tests)
- `tests/unit/test_tasks.py` (4+ tests)
- `tests/unit/test_event_log.py` (2+ tests)
- `tests/unit/test_session.py` (2+ tests)

**Schemas:** see RGIO.md

**Verify:** 12+ tests pass

**Commit:** `feat(s1): core session mailbox task event modules`

---

## S2 — Personas + project loader

**Files:**

- `src/agent_team/personas.py`
- `src/agent_team/project_loader.py`
- `personas/planner.yaml` (+ implementer, reviewer, tester)
- `templates/project/TEAM.md.j2`, `config.yaml.j2`
- `src/agent_team/cli/init.py`
- `tests/unit/test_personas.py`, `test_project_loader.py`

**Verify:** 8+ new tests

**Commit:** `feat(s2): personas and project init templates`

---

## S3 — CLI core

**Commands:**

- `agent-team mail send --session ID --to NAME --body TEXT`
- `agent-team mail read --session ID [--since last|ISO]`
- `agent-team task create|list|claim|complete`
- `agent-team logs tail --session ID [--follow]`
- `agent-team logs export --session ID --to PATH`
- `agent-team context show [--playbook NAME]` — preview lead injection
- `agent-team personas list`

**Files:** `src/agent_team/cli/mail.py`, `task.py`, `logs.py`, `personas.py`, `context.py`

**Verify:** CLI E2E with tmp session dir, 6+ tests

**Commit:** `feat(s3): mail task logs personas cli`

---

## S4 — PsmuxBackend

**File:** `src/agent_team/psmux_backend.py`

**Methods:** `new_session`, `split_pane`, `send_keys`, `kill_pane`, `list_panes`

**Verify:** mock subprocess tests always; `@pytest.mark.integration` if psmux in PATH

**Commit:** `feat(s4): psmux backend wrapper`

---

## S5 — Spawn approval

**File:** `src/agent_team/spawn_approval.py`

**Protocol:** `approval/pending.json` → user decision → `approval/resolutions.jsonl`

**Verify:** 6+ unit tests

**Commit:** `feat(s5): spawn approval queue`

---

## S6 — MCP server

**File:** `src/agent_team/mcp_server.py`

**Verify:** mock MCP client calls all tools; 10+ tests

**Commit:** `feat(s6): mcp server for team lead`

---

## S7 — Textual TUI

**Files:** `src/agent_team/tui/app.py`, `panels/mail.py`, `tasks.py`, `team.py`, `log.py`

**Order:** Mail + Log first → Tasks + Team → approval modal

**Verify:** pilot/snapshot tests; manual `textual run` smoke

**Commit:** `feat(s7): textual tui panels`

---

## S8 — Orchestrator dry-run

**Files:** `src/agent_team/orchestrator.py`, `teammate_runner.py` (mock), `cli/start.py`, `cli/attach.py`

**Flag:** `--dry-run` uses echo mock teammates, no real psmux required option `--no-psmux`

**Verify:** full dry-run cycle; 40+ total pytest

**Commit:** `feat(s8): orchestrator dry-run`

---

## S9 — Claude lead gate (LLM)

**Manual checklist:** `tests/manual/s9-claude-lead.md`

**Note:** `tests/fixtures/minimal-project/` is created in S8/S9 (not required for P0 docs).

1. psmux + `agent-team start` (no dry-run)
2. Claude lead + MCP config
3. One `spawn_teammate` → TUI approve
4. events.jsonl entry present

**Commit:** `feat(s9): claude lead integration verified`

---

## S10 — payment-api E2E (LLM)

**Fixture:** `tests/fixtures/payment-api/` or external `c:\DEV\payment-api`

**Manual:** playbook new-feature, refund API scenario

**Commit:** `feat(s10): payment-api e2e playbook`

---

## Test matrix summary

| Milestone | New tests (min) | Cumulative |
|-----------|-----------------|------------|
| S0 | 1 | 1 |
| S1 | 12 | 13 |
| S2 | 8 | 21 |
| S3 | 6 | 27 |
| S4 | 5 | 32 |
| S5 | 6 | 38 |
| S6 | 10 | 48 |
| S7 | 4 | 52 |
| S8 | 8 | 60 |

---

## Mock strategy

- `PsmuxBackend(mock=True)` records commands, no subprocess
- `MockTeammateRunner` spawns `python -c "print('ready')"`
- Session dirs under `tmp_path` pytest fixture

---

## P0.5 — Supplemental spec (schemas, MCP, dependencies)

Added after P0 to align with full design. **S1+ implementations MUST follow these.**

### §Schemas

#### session.json

```json
{
  "session_id": "agent-team-payment-api-a1b2",
  "project_path": "c:\\DEV\\payment-api",
  "psmux_session": "agent-team-payment-api-a1b2",
  "playbook": "new-feature",
  "playbook_mode": "guide",
  "created_at": "2026-06-10T12:00:00Z",
  "status": "active",
  "members": [
    {
      "name": "lead",
      "role": "lead",
      "persona": null,
      "cli": "claude",
      "pane_id": "%0",
      "backend": "psmux",
      "status": "running"
    },
    {
      "name": "planner-1",
      "role": "teammate",
      "persona": "planner",
      "cli": "claude",
      "pane_id": "%2",
      "backend": "psmux",
      "status": "running"
    }
  ],
  "max_teammates": 5
}
```

#### mailbox message (one JSONL line)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "from": "lead",
  "to": "planner-1",
  "body": "Please break down refund API tasks.",
  "ts": "2026-06-10T12:01:00Z"
}
```

#### task JSON (`tasks/task-001.json`)

```json
{
  "id": "task-001",
  "title": "Add refund schema",
  "description": "Pydantic models for POST /refunds",
  "state": "pending",
  "deps": [],
  "assignee": null,
  "created_at": "2026-06-10T12:02:00Z",
  "updated_at": "2026-06-10T12:02:00Z"
}
```

States: `pending` | `in_progress` | `completed`. Claim sets `assignee` + `in_progress`. Deps: task cannot claim until all deps `completed`.

#### event line (events.jsonl)

```json
{
  "type": "spawn_requested",
  "ts": "2026-06-10T12:00:30Z",
  "payload": {
    "persona": "planner",
    "cli": "claude",
    "requested_by": "lead"
  }
}
```

Event types (minimum): `session_started`, `spawn_requested`, `spawn_approved`, `spawn_denied`, `teammate_ready`, `teammate_shutdown`, `mail_sent`, `task_created`, `task_claimed`, `task_completed`, `error`.

#### approval/pending.json

```json
{
  "request_id": "apr-001",
  "persona": "implementer",
  "cli": "codex",
  "prompt_preview": "Implement tasks from board...",
  "requested_by": "lead",
  "requested_at": "2026-06-10T12:05:00Z",
  "status": "pending"
}
```

Resolution: append to `approval/resolutions.jsonl`:

```json
{
  "request_id": "apr-001",
  "decision": "approved",
  "decided_at": "2026-06-10T12:05:10Z",
  "decided_by": "user"
}
```

#### consumer `.agent-team/config.yaml`

See `templates/project/config.yaml.j2` and [project-integration.md](project-integration.md).

---

### §MCP Tools

**MCP is exposed to Team Lead (Claude) only.** All teammates (Claude or Codex) use `agent-team` CLI helpers for mail and tasks.

Server: `python -m agent_team.mcp_server`  
Config example: `templates/claude-mcp.json.example`

| Tool | Input | Output / side effects |
|------|-------|----------------------|
| `list_personas` | `{}` | `{personas: [{name, cli, description}]}` |
| `spawn_teammate` | `{persona, name?, prompt}` | Creates approval pending; returns `{request_id, status:"pending"}` |
| `shutdown_teammate` | `{name}` | Kills pane, updates session.json |
| `send_message` | `{to, body}` | Appends mailbox + event |
| `read_messages` | `{since?}` | `{messages: [...]}` for lead inbox |
| `create_task` | `{title, description?, deps?}` | Writes task JSON |
| `claim_task` | `{task_id, assignee?}` | Fails if deps incomplete |
| `complete_task` | `{task_id}` | Sets state completed |
| `list_teammates` | `{}` | `{members: [...]}` from session.json |

**spawn_teammate flow:**

1. Lead calls `spawn_teammate` → `pending.json` written, TUI notified
2. User approves in TUI → `resolutions.jsonl`, orchestrator spawns pane
3. MCP returns `{name, pane_id, status:"ready"}` to lead

---

### §Dependencies (pyproject.toml by milestone)

| Milestone | Add to dependencies | Add to dev |
|-----------|---------------------|------------|
| S0 | `click`, `pyyaml` | `pytest`, `ruff` |
| S1 | — | — |
| S3 | — | `pytest-click` (optional) |
| S6 | `mcp` or `fastmcp` | — |
| S7 | `textual`, `watchfiles` | — |
| S8 | `jinja2` (templates) | — |

---

### §Playbooks

Bundled reference copies in `docs/playbooks/`.  
`agent-team init` copies into consumer `.agent-team/playbooks/`.

**mode: guide** — YAML is hints for lead prompt only. Lead autonomously chooses spawns; user approves each spawn in TUI.

Samples: `new-feature.yaml`, `bugfix.yaml`, `pr-review.yaml`, `refactor.yaml`

---

### §Personas

Bundled in `personas/*.yaml`. Merge order:

1. `~/.agent-team/personas/`
2. `personas/` (package)
3. `./.agent-team/personas/` (project, highest priority)

Enforce `allowed_personas` from consumer `config.yaml` on spawn.

---

### §TUI spawn approval modal

Display when `approval/pending.json` exists:

- Persona name + CLI (`planner` / `claude`)
- Prompt preview (first 200 chars)
- Current teammate count / max (e.g. 2/5)
- Buttons: **Approve** / **Deny**

On approve: write resolution, clear pending, orchestrator continues spawn.

---

### §Orchestrator flags

| Flag | Behavior |
|------|----------|
| `--playbook NAME` | Load playbook YAML into lead context |
| `--context TEXT` | Extra user context (PR #, feature name) |
| `--dry-run` | Mock teammates, no real Claude/Codex |
| `--no-psmux` | TUI + file session only; no pane split |
| `--project PATH` | Consumer project root (default cwd) |

---

### §Related docs

- [architecture.md](architecture.md)
- [project-integration.md](project-integration.md)
- [tests/manual/s9-claude-lead.md](../tests/manual/s9-claude-lead.md)
- [tests/manual/s10-payment-api-e2e.md](../tests/manual/s10-payment-api-e2e.md)
