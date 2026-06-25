# Hermes 5-phase rollout — plan-eng-review (2026-06-25)

Reviewer: claude (plan-eng-review). Branch: s18. Input: Hermes company-test feedback
(5-phase rollout + hybrid orchestration; enterprise forbids auto-approve).

## Headline reframe

~80% of Hermes's "phases" are **already code-complete** (S9/S10 lead+teammate,
S16a manifest-final, S17 worktree, S18a external approver, S18b timeout/kill-all).
The phases are a **live-gate validation order over existing code**, NOT a build
backlog. Only 3 items need new code: 1A, 2C, 3A.

```
Hermes phase                         maps to                         status
P1 hermes+claude lead+claude mate    S9/S10 + S18a approver          ✅ code, live-gate pending
P2 codex read-only analyst           reviewer persona + tools_hint   ⚠️ persona yes, ENFORCE no (2a)
P3 codex/agy implementer @doctor     impl personas + doctor          ⚠️ personas yes, doctor no (2b)
P4 worktree+timeout+manifest+approval S17+S18b+S16a+S18a             ✅ all code-complete
P5 headless G5 autonomous            S18c checklist + autonomous     ✅ code+checklist, live pending
```

## Locked decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Enterprise no-auto-approve | **1A** two-tier deploy | enterprise = claude-team only (managed-perm, no `--dangerously-*`); codex/agy personal-mode only. Delegates enforcement to audited mechanisms; no single point of failure; "flag absent" is auditable. 1B (per-command Hermes approval) → TODOS. |
| 2 | `doctor` gate | **2C** hybrid | doctor codifies no-token deterministic checks (version/flags/subcommand/submit-keys) → exit gate; live token gates stay manual (`tests/manual/*-gates.md`). |
| 3 | Access-tier enforcement location | **3A** registry | `CliSpec` gains tier→launch-args map; runner picks by `persona.tools_hint`. Preserves "lead never names flags / persona never knows CLI" invariant (defended across CLI-registry-seam, S11c). |
| CQ-1 | 1A+3A code shape | single resolver | `resolve_launch_args(cli_spec, tools_hint, mode)` — one function, mode gate + tier map. DRY. |
| CQ-2 | tier mapping for `read-only-first` | **CQ-2B** planner=write | only `read-only` (reviewer) → hard read-only sandbox; `read-only-first` (planner) + `workspace-write` → write-capable (planner must write plan files). |
| CQ-3 | doctor's source of truth | **CQ-3C** registry | doctor asserts live CLI matches `cli_registry` expectations. Single source. |
| T2 | doctor testability | **T2C** pure core | pure decision function over injected probe results + thin IO shell (mirrors `manifest.py` pure projection). |
| T3 | read-only enforcement test | **T3A** unit + live | unit asserts flag present; manual live gate proves a read-only teammate's write actually fails (new row beside G0–G6). |

## Critical gap

`--sandbox read-only` may be **silently ignored by an old codex** → read-only persona
writes, no runtime detection. **Mitigation:** doctor's min-version check MUST be the
version that honors the flag; doctor gate runs before implementer is allowed (P3).

## Sequencing

1. **P1 live now** (no new build): claude lead + claude teammate + Hermes external
   approver → `tests/manual/s18a-external-approver.md`. Windows attended.
   - Caveat: Windows PowerShell-pane transcript 0-byte bug (Gs mtime-falsepos, OPEN)
     → STALE false positive on long no-output tasks. Short smoke OK.
2. Build **1A + 3A** together (same `resolve_launch_args` seam) → enterprise claude-team.
3. Build **2C doctor** → unblocks P3 codex/agy implementer gating.
4. P5 headless (needs claude-lead trust-bypass + auto-kickoff — TODOS).

## Deferred (NOT in scope)

1B Hermes per-command approval (TODOS); agy-LEAD S15b; S16c/d/e triage schema;
non-PowerShell transcript redirect (existing TODO); G5 live run (after 1A/2C/3A).
