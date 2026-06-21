# Windows setup

Prerequisites for developing and running **agent-team** on Windows 10/11. **No WSL.**

> **Linux / macOS?** agent-team is cross-platform since S13 — the terminal backend is
> factory-selected (psmux on Windows, **tmux ≥ 3.4** on Linux/macOS). For the Linux/tmux
> live runbook (claude lead + codex teammate, headless), see
> [../tests/manual/ubuntu-attended-runbook.md](../tests/manual/ubuntu-attended-runbook.md).

## Checklist

| Tool | Version | Install | Verify |
|------|---------|---------|--------|
| Python | 3.12+ | [python.org](https://www.python.org/) or `winget install Python.Python.3.12` | `python --version` |
| psmux | 0.4.10+ | `winget install psmux` | `psmux -V` |
| Claude CLI | latest | `npm install -g @anthropic-ai/claude-code` | `claude --version` |
| Codex CLI | latest | [OpenAI Codex CLI docs](https://developers.openai.com/codex/) | `codex --version` |
| agy (Antigravity) CLI | 1.0.10+ | *(optional — agy teammate, S12)* | `agy --version` |
| Git | any | `winget install Git.Git` | `git --version` (worktree isolation, S17, needs git) |

## agent-team (from source)

```powershell
cd c:\DEV\agent-team
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
pytest tests/ -q
```

## Cursor / AI coding helpers

- **Caveman (token saving):** `npx skills add JuliusBrussee/caveman -a cursor`
- If npm fails (corporate SSL): use [.cursor/rules/caveman.mdc](../.cursor/rules/caveman.mdc) (already in repo)

## When each tool is needed

| Milestone | Required |
|-----------|----------|
| S0–S8 | Python, Git |
| S4 integration tests | psmux (optional; mocks work without) |
| S9–S10 | psmux + Claude CLI (+ Codex for mixed teams) |
| S11–S18 | + Codex/agy CLIs for mixed teams; Git required for S17 worktree isolation; tmux ≥ 3.4 for Linux/macOS live gates |

## Consumer projects

See [project-integration.md](project-integration.md) for `agent-team init` on app repos.
