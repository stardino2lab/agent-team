# S10a — CLI-neutral teammate work foundation (design)

**Date:** 2026-06-14
**Status:** approved (brainstorming) — pending implementation plan
**Scope:** first slice of S10. Makes a spawned teammate able to do real work in
the consumer project, while preserving the CLI-neutral spawn invariant.

## Problem

S10 (payment-api E2E) needs teammates that actually edit project files, run
pytest, and use git. Two S9 code-review findings block this:

- **#7 — teammate cwd.** `TeammateRunner.spawn` runs the teammate CLI from
  `{session_dir}/teammates/{name}` (a scratch dir outside the project repo), so
  relative-path edits / pytest / git target the wrong place. The teammate
  cannot touch the project checkout.
- **#5 — prompt delivery.** The spawn prompt is sent via `send_keys` as a
  multi-line string; `psmux send_keys` types embedded newlines literally, and
  each newline acts as Enter in the teammate's interactive CLI, submitting the
  prompt line-by-line instead of as one coherent message.

## Binding constraint — CLI-neutral spawn invariant

The lead does **not** spawn teammates directly. It requests via the
`spawn_teammate` MCP tool; the CLI-neutral Python MCP server / `TeammateRunner`
performs the launch; the teammate CLI is decided by the persona. Code anchors:

- `spawn_teammate` has no CLI argument (`mcp_server.py:279`)
- `cli = persona_obj.cli` (`mcp_server.py:164`)
- `psmux.split_pane(command=persona.cli)` (`teammate_runner.py`)

> Do not make the lead exec teammates directly, and do not branch the launch
> per-CLI — that breaks the heterogeneous-team (mixed claude/codex/…) property.

A rejected earlier approach delivered context via a claude-specific flag
(`--append-system-prompt-file`), which would have introduced per-CLI launch
branching. Rejected for violating this invariant.

## Approach — A′ (CLI-neutral)

Change only `TeammateRunner.spawn`. The launch shape
(`split_pane(command=persona.cli, cwd=…)`) and the invariant are preserved; only
the **cwd** and the **trigger message** change.

| Element | Current | S10a |
|---------|---------|------|
| pane cwd | `{session_dir}/teammates/{name}` (scratch) | **`project_path`** (project root) |
| brief file | scratch `AGENTS.md` (relies on cwd auto-read) | scratch `AGENTS.md` (same location; no project pollution) |
| launch command | `persona.cli` (bare) | `persona.cli` (bare) — **unchanged, no per-CLI branch** |
| trigger | multi-line `full_prompt` via send_keys | **single-line kickoff** via send_keys |

### Data flow

```
spawn(persona, name, prompt, session_id, session_dir, project_path)
 1. render brief  -> {session_dir}/teammates/{name}/AGENTS.md
      (role template + coordination CLI + task = `prompt`)
 2. pane = split_pane(command=persona.cli, cwd=project_path)   # CLI-neutral; cwd -> project
 3. send_keys(pane, KICKOFF, enter=True)                       # single line
```

### Kickoff message (single line, no newlines)

> `You are agent-team teammate "{name}". Read your brief at {abs path to scratch AGENTS.md} — role, coordination CLI, and your task — then begin. Project conventions are in TEAM.md/AGENTS.md here.`

- Context delivery is a single "read this file" user message — the lowest common
  denominator across agentic CLIs (claude/codex/gemini all read a file on
  instruction). No per-CLI flag, no memory-file-convention dependency.
- Because cwd is the project root, the project's own `TEAM.md` / `AGENTS.md` /
  `CLAUDE.md` (team conventions) auto-load per each CLI's normal behavior; the
  scratch brief layers the per-persona role and task on top.
- The brief stays in the scratch dir, so the project repo is never written to or
  clobbered.

## Brief template

The existing `teammate/AGENTS.md.j2` becomes *more* correct under this change:
its "from the project directory" coordination commands and "Read TEAM.md in
project root" lines now match the actual cwd. No structural change required; it
keeps `--session {{ session_id }}` absolute coordination commands so cwd is not
load-bearing for mail/task.

## Error handling / edge cases

- **mock mode** (`mock=True`): unchanged — skips brief write + send_keys.
- **missing `project_path`**: already validated upstream in `Orchestrator.start`
  / `cli/start.py`.
- **teammate ignores the brief**: the project's own `AGENTS.md`/`TEAM.md`
  auto-loads from cwd, giving a baseline; reliable "read then act" behavior is a
  S10b (ready-handshake) concern, not S10a.
- **#5 hardening**: the kickoff is constructed as a single line by us;
  defensively collapse any newline to a space so a multi-line persona template
  can never reintroduce premature submission.

## Testing

Unit (`tests/unit/test_teammate_runner.py`, real mode):

- `split_pane` receives `cwd == project_path` (#7).
- launch command is the **bare `persona.cli`** with no flags — regression guard
  for the CLI-neutral invariant.
- `send_keys` payload is a **single line (no `\n`)** and contains the absolute
  path to the scratch `AGENTS.md` (#5).
- brief file still rendered at `{session_dir}/teammates/{name}/AGENTS.md` with
  persona, teammate name, session id, and the task prompt.

## Acceptance

Unit tests green is the S10a gate. Verifying that a real teammate actually
*does the work* requires the payment-api fixture and is deferred to S10c/S10d
(manual E2E). S10a guarantees only the launch mechanics.

## Out of scope (later S10 slices)

- **S10b** — real `teammate_ready` handshake (teammate writes a ready marker;
  orchestrator waits before emitting). Today's event still fires right after
  send_keys.
- **S10c** — payment-api fixture; verify codex teammate path end-to-end (codex
  uses the *same* CLI-neutral launch, so no per-CLI launch code is expected —
  only fixture + persona verification).
- **S10d** — run the manual payment-api E2E (acceptance gate).
- gemini / antigravity teammates — S11+.

## References

- `tests/manual/s10-payment-api-e2e.md` — the E2E scenario this enables.
- `docs/RGIO.md` — TeammateRunner / module contracts.
- `docs/s9-api-sketch.md` — teammate context decision this revises.
- PROGRESS.md — review findings #5, #7 (now scheduled into S10a).
