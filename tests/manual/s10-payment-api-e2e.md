# S10 — payment-api E2E manual scenario

**Requires:** S10a–S10c landed (teammate work foundation, ready handshake,
payment-api fixture), Claude + Codex CLI logged in, `pip install -e .`.

## Fixture

The fixture ships in this repo at `tests/fixtures/payment-api/`. The team will
WRITE code and run git inside the project, so copy it to a writable scratch dir
first to keep the agent-team repo clean:

```powershell
Copy-Item -Recurse tests\fixtures\payment-api $env:USERPROFILE\payment-api
cd $env:USERPROFILE\payment-api
git init ; git add -A ; git commit -m "baseline"
```

Layout (already present in the fixture):

```
payment-api/
  src/payment_service.py        # PaymentService.charge — the pattern to follow
  tests/test_payment.py         # passing baseline tests
  TEAM.md
  pyproject.toml                # pythonpath=src so `pytest tests/ -q` works
  .agent-team/config.yaml
  .agent-team/playbooks/new-feature.yaml
```

## Scenario: refund API

### 1. Start

```powershell
cd $env:USERPROFILE\payment-api
git checkout -b feature/refund-api
# --project is required; "." = this dir. Session id defaults to the dir name
# (payment-api).
agent-team start --project . --playbook new-feature
```

Expected psmux: `[ Lead | TUI | empty ]`

### 2. User instruction (lead pane)

```
POST /refunds API 추가. 기존 PaymentService 패턴 따를 것.
TEAM.md 준수. 완료 전 pytest 전부 통과.
```

### 3. Spawn approvals (TUI)

| # | Persona | CLI | Approve? |
|---|---------|-----|----------|
| 1 | planner | claude | Y |
| 2 | implementer | codex | Y |
| 3 | tester | codex | Y |
| 4 | reviewer | claude | Y |

### 4. Readiness handshake (S10b)

Each approved teammate launches in a pane **with the project as its cwd** (S10a)
and reads its brief (`{session_dir}/teammates/{name}/AGENTS.md`). Per the brief,
it runs once:

```powershell
agent-team teammate ready --session <id> --as <name>
```

- [ ] Event Log shows `teammate_ready` for a teammate **only after** that
      teammate signals ready (not immediately on spawn).
- [ ] TUI Team panel shows the member flip `[starting]` → `[running]`.

### 5. Expected team behavior

- planner: 4 tasks (schema, endpoint, service, tests)
- implementer: claims tasks, writes `src/refunds/`
- tester: runs `pytest tests/test_refunds.py`
- reviewer: mails feedback; implementer fixes if needed

### 6. Observe

- [ ] TUI Mail: cross-agent messages visible
- [ ] TUI Tasks: 4/4 completed
- [ ] psmux pane switch shows teammate output (each teammate working in the
      project dir — files actually change on disk)

### 7. Finish

```
Lead: 작업 마무리하고 팀원 종료해
```

The lead shuts teammates down via the `shutdown_teammate` MCP tool (kills the
pane + drops the member); confirm panes close.

```powershell
pytest tests/ -q
agent-team logs export --session last --to ./docs/agent-runs/
git status
```

### 8. Pass criteria

- [ ] pytest all pass
- [ ] every spawned teammate reached `teammate_ready` (real handshake — appeared
      only after the teammate signalled, not on spawn)
- [ ] Team panel showed `starting` → `running` per teammate
- [ ] `events.jsonl` exported; trail complete
      (`session_started → spawn_* → teammate_ready → teammate_shutdown →
      orchestrator_stopped`)
- [ ] psmux detach → attach → session alive (no re-spawn of handled teammates)
- [ ] `src/refunds/` and tests present in git diff

## Failure handling

- Spawn denied → lead should pick alternate plan
- CLI permission prompts → user approves in teammate pane only
- Token limit → stop at last stable task state; resume next session
