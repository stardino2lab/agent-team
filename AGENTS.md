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
- Multi-step work: plan with verify checkpoints per step.
- Run `pytest tests/ -q` before reporting milestone complete.

## Repo-specific guidance

| Doc | Read when |
|-----|-----------|
| [docs/agents/workflow.md](docs/agents/workflow.md) | Implementing a milestone |
| [docs/agents/git.md](docs/agents/git.md) | Before commit or push |
| [docs/agents/constraints.md](docs/agents/constraints.md) | Env and scope limits |

## References

- [docs/PRD.md](docs/PRD.md)
- [docs/RGIO.md](docs/RGIO.md)
- [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/project-integration.md](docs/project-integration.md)
- [docs/setup-windows.md](docs/setup-windows.md)
- [docs/playbooks/](docs/playbooks/)
