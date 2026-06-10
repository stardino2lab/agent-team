# Project integration — using agent-team on app repos

## Setup (once per project)

```powershell
cd c:\DEV\payment-api
agent-team init --template fastapi
git add TEAM.md .agent-team
git commit -m "Add agent-team project config"
```

## Daily workflow

```powershell
cd c:\DEV\payment-api
agent-team start --playbook new-feature
# psmux: Lead pane + TUI pane
```

Tell the lead (1–2 sentences):

```
POST /refunds API 추가. TEAM.md 준수. pytest 전부 통과 후 마무리.
```

## What you do vs what the team does

| You | Team |
|-----|------|
| `agent-team start` | Lead coordinates spawn/tasks |
| Goal in lead pane | planner → implementer → reviewer (autonomous) |
| Approve spawns in TUI (max 5) | Mailbox peer chat |
| Approve file/shell in CLI panes | Code, tests, review |
| Watch psmux + TUI | events.jsonl audit |
| `git commit` when done | Lead shuts down teammates |

## Playbook selection

| Playbook | Use when |
|----------|----------|
| `new-feature` | Cross-layer feature work |
| `bugfix` | Bug investigation |
| `pr-review` | PR/branch review (no code changes) |
| `refactor` | Large module refactor |

```powershell
agent-team start --playbook pr-review --context "PR #142"
agent-team context show    # preview lead injection (S3+)
```

## Git in consumer repo

| Path | Commit? |
|------|-----------|
| `TEAM.md` | Yes |
| `.agent-team/config.yaml` | Yes |
| `.agent-team/playbooks/` | Yes |
| `.agent-team/personas/` | Yes (optional domain personas) |
| `.agent-team/local/` | No |
| `docs/plans/*.md` | Yes (planner output, after review) |

## When NOT to use agent-team

- Single-file fix → use `claude` or `codex` alone
- Production hotfix → single CLI or `bugfix` playbook with minimal teammates
