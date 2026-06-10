# S10 — payment-api E2E manual scenario

**Requires:** S9 passed, Claude + Codex CLI logged in.

## Fixture

Use `tests/fixtures/payment-api/` (created in S10) or external `c:\DEV\payment-api`.

Minimal layout:

```
payment-api/
  src/payment_service.py
  tests/test_payment.py
  TEAM.md
  .agent-team/config.yaml
  .agent-team/playbooks/new-feature.yaml
```

## Scenario: refund API

### 1. Start

```powershell
cd payment-api
git checkout -b feature/refund-api
agent-team init   # if not done
agent-team start --playbook new-feature
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

### 4. Expected team behavior

- planner: 4 tasks (schema, endpoint, service, tests)
- implementer: claims tasks, writes `src/refunds/`
- tester: runs `pytest tests/test_refunds.py`
- reviewer: mails feedback; implementer fixes if needed

### 5. Observe

- [ ] TUI Mail: cross-agent messages visible
- [ ] TUI Tasks: 4/4 completed
- [ ] psmux pane switch shows teammate output

### 6. Finish

```
Lead: 작업 마무리하고 팀원 종료해
```

```powershell
pytest tests/ -q
agent-team logs export --session last --to ./docs/agent-runs/
git status
```

### 7. Pass criteria

- [ ] pytest all pass
- [ ] `events.jsonl` exported
- [ ] psmux detach → attach → session alive
- [ ] `src/refunds/` and tests present in git diff

## Failure handling

- Spawn denied → lead should pick alternate plan
- CLI permission prompts → user approves in teammate pane only
- Token limit → stop at last stable task state; resume next session
