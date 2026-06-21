# agent-team

Cross-platform multi-agent orchestrator for Claude CLI, Codex CLI, and agy (Antigravity).

- Team lead spawns teammates in terminal panes — **psmux** on Windows, **tmux** on Linux/macOS (one backend abstraction, factory-selected)
- Heterogeneous teams: **claude** + **codex** + **agy** teammates under a claude lead
- Shared **mailbox**, **task board**, and **JSONL audit log**
- **Textual TUI** *or* headless **external-approver** CLI for spawn approval
- **git-worktree isolation** per writer (blast-radius containment)
- **Daemon lifecycle**: graceful `stop` / `--timeout` / SIGTERM → a `final` result manifest
- **`agent-team status`** health snapshot + read-only result-manifest projection

## Status

**S11–S18 code-complete @ 2026-06-21 (branch `s15`–`s18`, 411 passed / 1 skipped, ruff clean) — live token/Linux/headless gates pending; not yet merged to main** — [한글 현황](docs/STATUS.ko.md) · [진행 로그](PROGRESS.ko.md) · [시각 현황](docs/blueprints/status.html) · [agent tracker](PROGRESS.md) · [다음 단계 로드맵](docs/s13-next-phase-roadmap.md)

Known live-gate state: claude lead + codex/agy teammate flow **PASS** (Windows); codex-as-lead **FAIL** (codex `exec` doesn't load the agent-team MCP); agy lead **deferred** (no `mcp` subcommand). Live gate index: [PROGRESS.md](PROGRESS.md) · [tests/manual/LIVE-GATES.md](tests/manual/LIVE-GATES.md).

| Doc | Purpose |
|-----|---------|
| [docs/STATUS.ko.md](docs/STATUS.ko.md) | Human-readable status (Korean) |
| [PROGRESS.ko.md](PROGRESS.ko.md) | Progress log + archive (Korean) |
| [PROGRESS.md](PROGRESS.md) | Agent milestone tracker (English, canonical) |
| [docs/blueprints/status.html](docs/blueprints/status.html) | Visual milestone dashboard |
| [AGENTS.md](AGENTS.md) | AI agent behavior + doc router |
| [docs/agents/workflow.md](docs/agents/workflow.md) | Milestone workflow |
| [docs/agents/git.md](docs/agents/git.md) | Commit/push rules |
| [docs/agents/constraints.md](docs/agents/constraints.md) | Env and scope limits |
| [docs/PRD.md](docs/PRD.md) | Requirements |
| [docs/RGIO.md](docs/RGIO.md) | Module contracts |
| [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) | S0–S18 milestone specs + schemas + MCP |
| [docs/architecture.md](docs/architecture.md) | Diagrams (backends, session dir, daemon lifecycle) |
| [docs/s13-next-phase-roadmap.md](docs/s13-next-phase-roadmap.md) | S13→S18 roadmap |
| [docs/s11-multi-cli-plan.md](docs/s11-multi-cli-plan.md) | S11/S12 multi-CLI plan (D1–D12) |
| [docs/project-integration.md](docs/project-integration.md) | Using on app repos |
| [docs/hermes-integration.md](docs/hermes-integration.md) | Driving agent-team from an upstream orchestrator (Hermes) — agent-facing contract |
| [tests/manual/ubuntu-attended-runbook.md](tests/manual/ubuntu-attended-runbook.md) | Linux/tmux live runbook |

## Prerequisites

See **[docs/setup-windows.md](docs/setup-windows.md)** for Windows install; Linux/macOS uses tmux — see [tests/manual/ubuntu-attended-runbook.md](tests/manual/ubuntu-attended-runbook.md).

- Windows 10/11 (no WSL) **or** Linux/macOS
- Python 3.12+
- Terminal backend: **psmux 0.4.10+** (Windows) **or** **tmux ≥ 3.4** (Linux/macOS)
- Claude CLI (lead + teammate), Codex CLI (teammate; lead under spike) — optional: agy/Antigravity CLI (teammate)

## License

MIT (TBD at S0)
