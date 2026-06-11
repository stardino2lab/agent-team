# Expert axes template

Copy this block into the milestone plan or review prompt. Replace `{N}`, paths, and axes per IMPLEMENTATION §.

## Milestone `{N}` — plan review axes

| ID | Focus | Checklist |
|----|-------|-----------|
| E1 Schema | RGIO + IMPLEMENTATION §Schemas | Field names, states, event payloads, defaults |
| E2 API | Sketch function signatures | Exceptions, inject deps, no scope creep |
| E3 Tests | Sketch test matrix | Fixture isolation, error paths, matrix row count |
| E4 Downstream | Next milestone contracts | MCP/TUI/orchestrator parity hints |
| E5 *optional* | Milestone-specific | e.g. Init CLI, Packaging, Commands, CLI-UX |

**Files (plan):** `docs/s{N}-api-sketch.md`, `docs/RGIO.md`, `docs/IMPLEMENTATION.md` §S{N}

**Gate:** BLOCKING=0 → implement

---

## Milestone `{N}` — code review axes

Reuse plan axes; shift checklist to **implementation**.

| ID | Focus | Checklist (code) |
|----|-------|------------------|
| E1 Schema | RGIO vs on-disk JSON | Same as plan + serialization in code |
| E2 API / Security | Library + CLI | `safe_segment`, typed errors, thin wrap |
| E3 Integration | S1/S2 reuse | EventLog on mutations; no duplicated logic |
| E4 Tests | `tests/unit/` | Matrix covered; isolation (`AGENT_TEAM_HOME`, personas) |
| E5 Downstream | S6+ parity | CLI ≈ future MCP tools; cursor/env semantics |

**Files (code):** list from IMPLEMENTATION §S{N} + tests + sketch

**Gate:** BLOCKING=0; fix P1 → pytest + ruff green → commit approval

---

## Examples from this repo

### S1 (4 experts)

E1 Schema, E2 API/Security, E3 Tests, E4 Downstream

### S2 (5 experts)

E1 Schema, E2 API, E3 Init CLI, E4 Tests, E5 Packaging/bundled

### S3 (5 experts)

E1 Commands, E2 CLI UX, E3 Integration, E4 Tests, E5 Downstream (S6 MCP)

---

## Subagent launch checklist

```
- [ ] Mode: plan | code
- [ ] N experts defined (4–6)
- [ ] File list attached to each prompt
- [ ] All Task calls in one parallel batch
- [ ] readonly: true
- [ ] Triage table written
- [ ] BLOCKING fixed; P1 per gate rules
- [ ] pytest + ruff
- [ ] PROGRESS.md updated (code gate)
```
