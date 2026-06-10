# Windows setup

Prerequisites for developing and running **agent-team** on Windows 10/11. **No WSL.**

## Checklist

| Tool | Version | Install | Verify |
|------|---------|---------|--------|
| Python | 3.12+ | [python.org](https://www.python.org/) or `winget install Python.Python.3.12` | `python --version` |
| psmux | 0.4.10+ | `winget install psmux` | `psmux -V` |
| Claude CLI | latest | `npm install -g @anthropic-ai/claude-code` | `claude --version` |
| Codex CLI | latest | [OpenAI Codex CLI docs](https://developers.openai.com/codex/) | `codex --version` |
| Git | any | `winget install Git.Git` | `git --version` |

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

## Consumer projects

See [project-integration.md](project-integration.md) for `agent-team init` on app repos.
