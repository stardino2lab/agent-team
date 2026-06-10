# Agent git workflow

Git rules for AI agents working on this repository.

## Commit and push

- **No commit or push without user approval** (except when user explicitly requests for a milestone gate)
- **One milestone = one commit:** `docs(p0):`, `feat(s1):`, etc.
- No force push

## Report before commit

Include in your milestone report:

- Changed files
- Test results (`pytest tests/ -q`)
- Proposed commit message

Wait for user approval before `git add` / `git commit` / `git push`.
