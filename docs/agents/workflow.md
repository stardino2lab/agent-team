# Agent workflow — milestones

How to implement work in this repository.

## One session = one milestone

Follow the current milestone in [IMPLEMENTATION.md](../IMPLEMENTATION.md). Check [PROGRESS.md](../../PROGRESS.md) for status and next action. Human-readable Korean status: [STATUS.ko.md](../STATUS.ko.md), [PROGRESS.ko.md](../../PROGRESS.ko.md).

Module contracts live in [RGIO.md](../RGIO.md). Do not violate them.

## Before coding

Define verifiable success criteria for the milestone. Multi-step work: plan with verify checkpoints per step.

## Before reporting done

```powershell
pytest tests/ -q
```

All tests must pass.

## After milestone complete

1. Update [PROGRESS.md](../../PROGRESS.md) (English rolling status).
2. Update [PROGRESS.ko.md](../../PROGRESS.ko.md) — rolling section + append **완료 이력 (아카이브)** entry (Korean, 3–5 bullets).
3. Update [STATUS.ko.md](../STATUS.ko.md) — feature table, next steps, test count.
4. Update [blueprints/status.html](../blueprints/status.html) — gate colors and milestone table row.

Then report to the user: changed files, test results, proposed commit message. See [git.md](git.md) for commit rules.
