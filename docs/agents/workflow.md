# Agent workflow — milestones

How to implement work in this repository.

## One session = one milestone

Follow the current milestone in [IMPLEMENTATION.md](../IMPLEMENTATION.md). Check [PROGRESS.md](../../PROGRESS.md) for status and next action.

Module contracts live in [RGIO.md](../RGIO.md). Do not violate them.

## Before coding

Define verifiable success criteria for the milestone. Multi-step work: plan with verify checkpoints per step.

## Before reporting done

```powershell
pytest tests/ -q
```

All tests must pass.

## After milestone complete

Update [PROGRESS.md](../../PROGRESS.md) with completed work and next action.

Then report to the user: changed files, test results, proposed commit message. See [git.md](git.md) for commit rules.
