# agent-team

Windows-native multi-agent orchestrator for Claude CLI and Codex CLI.

- Team lead spawns teammates in **psmux** panes
- Shared **mailbox**, **task board**, and **JSONL audit log**
- **Textual TUI** for spawn approval and real-time monitoring

## Status

**S7 complete — next S8 orchestrator** — [한글 현황](docs/STATUS.ko.md) · [진행 로그](PROGRESS.ko.md) · [시각 현황](docs/blueprints/status.html) · [agent tracker](PROGRESS.md)

| Doc | Purpose |
|-----|---------|
| [docs/STATUS.ko.md](docs/STATUS.ko.md) | Human-readable status (Korean) |
| [PROGRESS.ko.md](PROGRESS.ko.md) | Progress log + archive (Korean) |
| [docs/blueprints/status.html](docs/blueprints/status.html) | Visual milestone dashboard |
| [AGENTS.md](AGENTS.md) | AI agent behavior + doc router |
| [docs/agents/workflow.md](docs/agents/workflow.md) | Milestone workflow |
| [docs/agents/git.md](docs/agents/git.md) | Commit/push rules |
| [docs/agents/constraints.md](docs/agents/constraints.md) | Env and scope limits |
| [docs/PRD.md](docs/PRD.md) | Requirements |
| [docs/RGIO.md](docs/RGIO.md) | Module contracts |
| [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) | S0–S10 + schemas + MCP |
| [docs/architecture.md](docs/architecture.md) | Diagrams |
| [docs/project-integration.md](docs/project-integration.md) | Using on app repos |
| [PROGRESS.md](PROGRESS.md) | Agent milestone tracker (English) |

## Prerequisites

See **[docs/setup-windows.md](docs/setup-windows.md)** for install steps.

- Windows 10/11 (no WSL)
- Python 3.12+
- psmux 0.4.10+ (S4+ / S9+)
- Claude CLI, Codex CLI (S9+)

## License

MIT (TBD at S0)
