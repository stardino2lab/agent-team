# IMPLEMENTATION — S0 through S10

Milestone spec for `c:\DEV\agent-team`.  
**Workflow:** implement → `pytest` / checklist → report → user approve → commit → (optional) push.

---

## P0 — Documentation (done)

**Deliverables:** PRD, RGIO, AGENTS.md, IMPLEMENTATION (this file), PROGRESS, README, `.gitignore`, `.cursor/rules/caveman.mdc`

**Verify:** checklist in AGENTS.md; no `src/` yet.

**Commit:** `docs(p0): initial project documentation`

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

**Commands:** `mail send/read`, `task create/list/claim/complete`, `logs tail`, `personas list`

**Files:** `src/agent_team/cli/mail.py`, `task.py`, `logs.py`, `personas.py`

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
