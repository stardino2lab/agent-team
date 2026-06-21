# AGENTS.md — agent-team orchestrator

Rules for AI agents (Cursor, Claude Code, Codex) building this repository.

## Communication

Terse replies — see [.cursor/rules/caveman.mdc](.cursor/rules/caveman.mdc).

## Behavioral Guidelines

Derived from [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills).

### 1. Think Before Coding

- State assumptions. If uncertain, ask.
- Present multiple interpretations — do not pick silently.
- If a simpler approach exists, say so.
- If unclear, stop and name what is confusing.

### 2. Simplicity First

- No features beyond the current milestone.
- No abstractions for single-use code.
- No unrequested flexibility or config.
- No error handling for impossible scenarios.

### 3. Surgical Changes

- Touch only what the milestone requires.
- Do not refactor unrelated code.
- Match existing style.
- Every changed line must trace to the milestone scope.

### 4. Goal-Driven Execution

- Define verifiable success criteria before coding.
- **Plan-first**: before writing/editing code, write a plan document and get approval first. Exceptions: trivial edits, or the user says "just do it". Details: [docs/agents/planning.md](docs/agents/planning.md).
- Multi-step work: plan with verify checkpoints per step.
- Run `pytest tests/ -q` before reporting milestone complete.

## Repo-specific guidance

| Doc | Read when |
|-----|-----------|
| [docs/agents/planning.md](docs/agents/planning.md) | Writing a plan document before implementing |
| [docs/agents/workflow.md](docs/agents/workflow.md) | Implementing a milestone |
| [.cursor/skills/review-expert/SKILL.md](.cursor/skills/review-expert/SKILL.md) | Plan or code expert review gate |
| [docs/agents/git.md](docs/agents/git.md) | Before commit or push |
| [docs/agents/constraints.md](docs/agents/constraints.md) | Env and scope limits |

## References

- [PROGRESS.md](PROGRESS.md) — canonical milestone tracker (S0–S18); [PROGRESS.ko.md](PROGRESS.ko.md) / [docs/STATUS.ko.md](docs/STATUS.ko.md) are the Korean mirror
- [docs/PRD.md](docs/PRD.md)
- [docs/RGIO.md](docs/RGIO.md)
- [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) — S0–S18 specs + schemas + MCP
- [docs/architecture.md](docs/architecture.md)
- [docs/s13-next-phase-roadmap.md](docs/s13-next-phase-roadmap.md) — S13→S18 roadmap
- [docs/project-integration.md](docs/project-integration.md)
- [docs/setup-windows.md](docs/setup-windows.md) (Windows) · [tests/manual/ubuntu-attended-runbook.md](tests/manual/ubuntu-attended-runbook.md) (Linux/tmux)
- [docs/playbooks/](docs/playbooks/)
