# Agent constraints — this repo

Environment, layout, and scope limits for building **agent-team**.

## Project layout

- **Path:** `c:\DEV\agent-team`
- **Package:** `src/agent_team/` (from S0)

## Language and tooling

- **Python:** 3.12+, type hints, ruff
- **Tests:** pytest required for S1+; mock only for S0–S8

## Platform

- **Windows + psmux only** — no WSL

Install details: [setup-windows.md](../setup-windows.md)

## Out of scope (until S10 done)

- Phase 2 web dashboard
- Codex as team lead
- Built-in Claude Agent Teams (we build custom orchestrator)

See also [PRD.md](../PRD.md) for product scope.
