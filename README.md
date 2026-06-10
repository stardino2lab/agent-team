# agent-team

Windows-native multi-agent orchestrator for Claude CLI and Codex CLI.

- Team lead spawns teammates in **psmux** panes
- Shared **mailbox**, **task board**, and **JSONL audit log**
- **Textual TUI** for spawn approval and real-time monitoring

## Status

**P0 + P0.5 complete** — documentation and supplemental spec. Implementation starts at S0.

| Doc | Purpose |
|-----|---------|
| [docs/PRD.md](docs/PRD.md) | Requirements |
| [docs/RGIO.md](docs/RGIO.md) | Module contracts |
| [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) | S0–S10 + schemas + MCP |
| [docs/architecture.md](docs/architecture.md) | Diagrams |
| [docs/project-integration.md](docs/project-integration.md) | Using on app repos |
| [PROGRESS.md](PROGRESS.md) | Milestone tracker |

## Prerequisites

See **[docs/setup-windows.md](docs/setup-windows.md)** for install steps.

- Windows 10/11 (no WSL)
- Python 3.12+
- psmux 0.4.10+ (S4+ / S9+)
- Claude CLI, Codex CLI (S9+)

## License

MIT (TBD at S0)
