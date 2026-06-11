---
name: review-expert
description: >-
  Run N-expert parallel plan or code review gates with BLOCKING/P1/P2 triage.
  Use when the user asks for expert review, plan review gate, code review gate,
  milestone review, or BLOCKING=0 before implement/commit in agent-team.
disable-model-invocation: true
---
# Review Expert

Milestone review gate for this repository. Two modes share the same process; only inputs and fix targets differ.

| Mode | When | Input | Gate pass → |
|------|------|-------|-------------|
| **plan** | Before implementation | API sketch + RGIO + IMPLEMENTATION § | Implement |
| **code** | After implementation, before commit | Changed code + tests + sketch/spec | User-approved commit |

Do not edit plan files (`.cursor/plans/*.plan.md`) unless the user explicitly asks.

## Quick start

1. Read milestone context: `docs/IMPLEMENTATION.md` (current §), `docs/PROGRESS.md`, `docs/s*-api-sketch.md` if present.
2. Pick mode: **plan** or **code** (user intent or milestone phase).
3. Define expert axes for this milestone — use [axes-template.md](axes-template.md); copy axes into the review prompt.
4. Run baseline (code mode only): `pytest tests/ -q` and `ruff check src tests`.
5. Launch **N parallel** `Task` subagents (`readonly: true`, `subagent_type: explore`).
6. Triage all findings → fix **BLOCKING**; fix **P1** when gate requires it (this repo: plan gate = BLOCKING only; code gate = BLOCKING + P1).
7. Re-run pytest + ruff; update `PROGRESS.md`; report triage table + proposed commit message.

## Expert count

| Milestone shape | Experts |
|-----------------|---------|
| Core data / thin layer | 4 |
| + CLI, packaging, init | 5 |
| + templates, extra surface | 6 |

Default **5** when unsure. Each expert = one Task with a focused checklist.

## Subagent prompt shape

```text
{Plan|Code} review: {milestone id} — {axis name}

Focus: {checklist from axes}

Files:
- {absolute or repo-relative paths}

Spec:
- docs/{sketch}.md
- docs/IMPLEMENTATION.md §{section}
- docs/RGIO.md (relevant §)

Return:
## Findings
- [BLOCKING|P1|P2] path:line — issue + rationale

## OK
- bullet summary

Verdict: BLOCKING count
```

Launch all experts in **one message** (parallel Task calls).

## Finding severity

| Level | Meaning | Gate |
|-------|---------|------|
| **BLOCKING** | Wrong contract, security/path traversal, broken tests, S6 downstream break | Must fix before proceed |
| **P1** | Correctness/UX/isolation gap; should fix before commit | Fix in code gate; optional in plan gate (update sketch) |
| **P2** | Doc drift, nits, optional tests | Report only unless user asks |

## Triage report template

```markdown
## Expert triage

| Expert | Focus | BLOCKING | P1 | Verdict |
|--------|-------|----------|-----|---------|
| E1 … | … | 0 | … | pass/fail |

**Gate:** BLOCKING=0 (and P1 fixed for code gate)

### Fixes applied
- …

### Verify
- pytest: N passed
- ruff: clean
```

## Mode: plan review

**Before** writing implementation code.

1. Ensure API sketch exists (`docs/s{N}-api-sketch.md`) — create if milestone plan says so.
2. Assign 4–6 expert axes (Schema, API, Tests, Downstream, + milestone-specific).
3. Parallel plan review on **sketch + docs**, not implementation.
4. **BLOCKING=0** → implement. P1 → update sketch/spec, then re-review affected experts only.
5. Do not commit until implementation + code gate (unless user only wanted plan gate).

## Mode: code review

**After** implementation, **before** commit.

1. Baseline: `pytest tests/ -q`, `ruff check src tests`, optional CLI smoke.
2. Same or refined axes as plan review, but review **source + tests**.
3. Fix **BLOCKING + P1** (this repo standard per S2/S3 code gates).
4. Re-verify; update `PROGRESS.md` with code-review fixes.
5. Propose commit — do not commit without user approval (`AGENTS.md`).

Suggested commit after code gate:

```text
feat(s{N}): …
```

Or fix-only follow-up:

```text
fix(s{N}): code review — …
```

## Project rules (agent-team)

- Surgical fixes only — no unrelated refactor (`AGENTS.md`).
- Windows + psmux; mock tests S0–S8.
- One milestone per session; `pytest tests/ -q` before reporting done.
- Expert axes and file lists change per milestone — always read current IMPLEMENTATION §, not hardcoded S3 lists.

## Related skills

- **review-bugbot** — single diff bug hunt; use for PR/branch review, not milestone spec gate.
- **review-security** — security-focused diff review; optional after code gate.

## Reference

- Expert axis worksheet: [axes-template.md](axes-template.md)
- Past examples: `docs/s1-api-sketch.md`, `docs/s2-api-sketch.md`, `docs/s3-api-sketch.md`
