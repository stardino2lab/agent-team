# AGENTS.md — agent-team orchestrator

Rules for AI agents (Cursor, Claude Code, Codex) building this repository.

## Communication (S0–S8 implementation)

Use caveman skill full — terse replies, keep code/tests/schemas complete.

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

## Project-Specific Rules

- **Path:** `c:\DEV\agent-team`
- **Layout:** `src/agent_team/` package (from S0)
- **Python:** 3.12+, type hints, ruff
- **Tests:** pytest required for S1+; mock only for S0–S8
- **Milestones:** one per session — follow `docs/RGIO.md` + `docs/IMPLEMENTATION.md`
- **Windows + psmux only** — no WSL
- **PROGRESS.md:** update at end of each milestone

## Git Workflow

- **No commit or push without user approval** (except when user explicitly requests for a milestone gate)
- **One milestone = one commit:** `docs(p0):`, `feat(s1):`, etc.
- No force push
- Report: changed files, test results, proposed commit message

## Out of Scope (until S10 done)

- Phase 2 web dashboard
- Codex as team lead
- Built-in Claude Agent Teams (we build custom orchestrator)

## References

- [docs/PRD.md](docs/PRD.md)
- [docs/RGIO.md](docs/RGIO.md)
- [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md)
