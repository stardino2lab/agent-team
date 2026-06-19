# PRD — agent-team Orchestrator

## 1. Summary

**agent-team** is a Windows-native CLI tool that orchestrates **Claude CLI** and **Codex CLI** as a supervised multi-agent team: one team lead, spawnable teammates, shared mailbox and tasks, psmux split panes, and a Textual TUI.

## 2. Problem

- Claude built-in Agent Teams does not work well on Windows without workarounds.
- Company developers need parallel personas (planner, implementer, reviewer) with audit trails.
- LLM subscription limits require mock-first development and token-aware workflows.

## 3. Users

| User | Need |
|------|------|
| Developer | Start team session on a project, approve spawns, watch panes/TUI |
| Team lead (Claude) | Spawn/shutdown teammates, tasks, mailbox via MCP |
| Teammates | Role-based CLI sessions with shared coordination |

## 4. Goals

1. Custom orchestrator (not Claude experimental agent teams).
2. psmux pane per agent + TUI for mail/tasks/approval/log.
3. Persistent JSONL audit log per session.
4. Project integration via `.agent-team/` + `TEAM.md` (consumer repos).
5. P0–S8 implementable without live Claude/Codex API calls.

## 5. Non-Goals (Phase 1)

- Web dashboard (Phase 2)
- Codex as team lead (Phase 2 — now scheduled as **S11c**; agy/Antigravity as **S12**)
- WSL / Linux support
- Nested agent teams (teammates spawning teammates)

## 6. Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-01 | `agent-team start` creates psmux session with lead + TUI panes |
| FR-02 | Lead uses MCP: spawn, shutdown, send_message, read_messages, task CRUD |
| FR-03 | Spawn requires user approval in TUI |
| FR-04 | Mailbox: peer messaging lead ↔ teammates ↔ teammates |
| FR-05 | Task board: pending / in_progress / completed + dependencies |
| FR-06 | Event log: append-only JSONL |
| FR-07 | `agent-team init` scaffolds `.agent-team/` + TEAM.md in consumer project |
| FR-08 | Personas YAML: `cli: claude \| codex` per role |
| FR-09 | Playbooks as **guide** hints to lead (not hard pipeline) |
| FR-10 | `agent-team start --dry-run` for S8 mock E2E |
| FR-11 | `agent-team attach` after psmux detach |
| FR-12 | `agent-team logs export` for audit |
| FR-13 | `agent-team context show` previews lead injection |
| FR-14 | Playbook `mode: guide` — hints only, lead autonomously spawns |

## 7. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-01 | Windows 10/11 native, psmux 0.4.10+ |
| NFR-02 | Max 5 concurrent teammates |
| NFR-03 | Individual CLI OAuth per developer machine |
| NFR-04 | S0–S8: pytest-only verification |
| NFR-05 | Single source of truth: session dir JSON/JSONL |
| NFR-06 | Milestone delivery: implement → verify → user approve → commit |

## 8. Success Metrics (MVP / S10) — ✅ met 2026-06-15

- [x] `payment-api` fixture: init + start + playbook new-feature
- [x] Spawn approval + mailbox visible in TUI
- [x] events.jsonl exportable
- [x] psmux detach/attach preserves session (`agent-team attach`)
- [x] 40+ pytest tests passing at S8 (216 passing at S10)

S10 manual E2E passed with real tokens: a heterogeneous Claude+Codex team under a
Claude lead built a refund feature, tests green, reviewer APPROVED.

## 9. Constraints

- No WSL
- Small LLM quota → document-first (P0), mock-first (S0–S8)
- Commit/push only on user approval per milestone

## 10. Milestones

- **P0 → S10** — [IMPLEMENTATION.md](IMPLEMENTATION.md). All complete (S10 E2E passed 2026-06-15).
- **S11 / S12** — multi-CLI (codex 2nd lead, agy/Antigravity) + $20-lead token/observability hardening: [s11-multi-cli-plan.md](s11-multi-cli-plan.md).
