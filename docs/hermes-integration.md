# Hermes integration — driving agent-team as an unattended worker

> **Audience:** an upstream orchestrator agent ("Hermes") that shells out to the
> `agent-team` CLI, approves spawns, and reads results back — with **no human at
> the terminal**. Give this single document to that agent as its operating
> contract. It is self-contained; you should not need to read the source.
>
> Pinned to `manifest_version: 2`. If the manifest envelope changes, this doc and
> the version bump move together.

---

## 0. One-time bootstrap (setup, NOT per-run)

Do this **once** per host + per consumer repo before any session. It is outside
the per-run contract (§3) — a fresh environment cannot skip it.

**a. Host tools** (see [setup-windows.md](setup-windows.md) for the full table):

```bash
pip install -e .                      # install agent-team (from source); puts `agent-team` on PATH
npm install -g @anthropic-ai/claude-code   # at least one teammate CLI...
# + codex per OpenAI docs; tmux ≥ 3.4 on headless Linux; git (required for worktrees)
agent-team --version                  # verify on PATH
```

**b. Authenticate the teammate CLIs** (interactive, one-time):

```bash
claude     # complete login once; token persists in ~/.claude
codex      # likewise in ~/.codex
```

Unattended runs cannot do an interactive login — the CLIs must already be
authenticated. agy has no sandbox; keep it out of unattended sessions (§2).

**c. Onboard the consumer repo** (once per repo):

```bash
cd <repo>                             # must be a git repo with ≥1 commit
agent-team init --template fastapi    # scaffolds TEAM.md + .agent-team/{config.yaml,playbooks,personas}
```

Then **enable worktree containment** — `init` leaves it commented out, but
unattended runs require it. Edit `.agent-team/config.yaml`:

```yaml
isolate_worktrees: true               # REQUIRED for unattended; init ships it commented out
```

Commit `TEAM.md` + `.agent-team/` (minus `local/`). Edit `TEAM.md` to describe the
repo's stack, test command, and forbidden paths — the lead reads it every run.

> **Verification (read-only, no tokens):**
> `agent-team context show --project <repo>` assembles and prints the lead context
> from `TEAM.md` + config + playbook. If it prints the context, the repo is
> onboarded and the binary is on PATH; if it errors (`TeamMdNotFound` /
> `ProjectConfig`), fix bootstrap before starting a real session.

---

## 1. Your role

agent-team runs a team of CLI coding agents (a lead + teammates) inside terminal
panes. **You are the external approver and the completion judge.** You do three
things and nothing else:

1. **Start** a session (backgrounded, with a mandatory timeout).
2. **Approve / deny** each spawn request as it appears (you are `--by hermes`).
3. **Read the result manifest** and act **only when `final: true`**.

You do **not** tell teammates what to do mid-run, and you do **not** judge task
difficulty — agent-team gives you no difficulty score. All scoping is yours,
up front, in the goal you hand the lead.

```
   ┌─────────┐  start --autonomous --timeout N &   ┌──────────────────────┐
   │ HERMES  │ ───────────────────────────────────▶│  agent-team session  │
   │ (you)   │                                      │  lead + teammates    │
   │         │  ◀── spawn_requested (events) ────── │  in detached panes   │
   │         │  ── approvals approve --by hermes ──▶│                      │
   │         │                                      │                      │
   │         │  ── logs manifest --format json ───▶ │  (poll for final)    │
   │         │  ◀── { final, session_status, ... } ─│                      │
   └─────────┘                                      └──────────────────────┘
```

---

## 2. Preconditions (verify before start)

- A consumer project that is a **git repo with ≥1 commit**, containing
  `.agent-team/config.yaml` with **`isolate_worktrees: true`** (worktree
  containment is REQUIRED for unattended runs) and a cost-sane
  `allowed_personas`.
- At least one teammate CLI authenticated (`claude` and/or `codex`).
  **`agy` has no sandbox flag — keep agy teammates OUT of unattended sessions**,
  or run the whole session inside a container/VM.
- A **globally-unique session id** — mint a UUID suffix. The default
  (`project.name`) collides on retries.
- `agent-team` on `PATH`; on headless Linux, `tmux ≥ 3.4` installed.

> **This doc assumes the above already exist — it does not bootstrap them.**
> Installing `agent-team`, authenticating the CLIs, and onboarding a repo
> (`agent-team init` → commit `TEAM.md` + `.agent-team/`) are one-time setup
> outside this contract. See [setup-windows.md](setup-windows.md) and
> [project-integration.md](project-integration.md). If a repo is not yet
> onboarded, `start` fails fast with a `TeamMdNotFound`/`ProjectConfig` error.

---

## 3. The lifecycle (copy-paste command sequence)

### a. Start — backgrounded, autonomous, with a mandatory timeout

```bash
agent-team start \
  --project <repo> \
  --session <uuid> \
  --playbook <name> \                # optional; else config default_playbook
  --context "<the goal for the team>" \   # REQUIRED in unattended mode — see below
  --autonomous \
  --timeout <N> &        # seconds; REQUIRED with --autonomous (liveness backstop)
```

- **`--context` is how you hand the team its goal.** In attended mode a human
  types the goal into the lead pane; unattended there is no human, so the lead's
  only task channel is `--context`. It is appended to the lead's context as an
  "Extra context" section (alongside the project's `TEAM.md` + the playbook).
  Omit it and the team runs the bare playbook with **no specific task** — almost
  never what you want. Write the goal as the 1–2 sentence instruction you would
  have typed (e.g. `POST /refunds API 추가. TEAM.md 준수. pytest 통과 후 마무리.`).
- `--playbook` selects the workflow shape (`new-feature`, `bugfix`, `pr-review`,
  `refactor`); omit to use the project's `default_playbook`.
- `--autonomous` without `--timeout` is rejected before any pane spawns.
- The process **blocks its shell on purpose** (it drives approvals). Background it
  (`&` on POSIX) so your script keeps running; do **not** close the shell.
- `--timeout` kills **all** panes on expiry — the hard backstop against hangs.

### b. Watch for pending spawns

```bash
agent-team logs tail --session <uuid> --follow      # stream events
# each spawn surfaces as a `spawn_requested` event
agent-team approvals list --session <uuid> --json    # one-shot: the pending request
```

`approvals list --json` returns `{ "pending": { "request_id": "apr-NNN",
"persona", "cli", "prompt_preview", ... } }` or `{ "pending": null }`. The gate is
**single-pending** — resolve the current one before the next appears.

### c. Resolve every spawn (you are the approver)

```bash
agent-team approvals approve --session <uuid> --id <apr-NNN> --by hermes
# or
agent-team approvals deny    --session <uuid> --id <apr-NNN> --by hermes
```

This produces the exact same `resolutions.jsonl` + event + cleared-pending state a
human TUI approval would; the spawn proceeds identically, attributed
`decided_by: "hermes"`. No TUI ever opens.

### d. Wait for completion — poll the manifest, act ONLY on `final: true`

```bash
agent-team logs manifest --session <uuid> --format json
```

See §4 for the contract. A mid-run read returns `final: false` — **you must not
act on it.** `logs manifest` is a pure projection; it is safe to call any time and
works even after an orchestrator crash (no cache needed).

### e. Optional: live health snapshot (does not signal completion)

```bash
agent-team status --session <uuid> --json     # exits 2 if the team is unhealthy
```

Use for liveness/escalation visibility only. **Never** treat task state here as
"done" — only the manifest's `final` flag means done.

---

## 4. The completion contract (the one rule that matters)

> **Act ONLY when the manifest's `final` is `true`.**

`logs manifest` is callable at any moment, so a naive read mid-run would report
in-progress tasks as "the answer." `final: true` is set **only** after a terminal
`orchestrator_stopped` event — i.e. the session has stopped and will not
re-attach. Until then:

| `final` | meaning | your action |
| --- | --- | --- |
| `false` | session still running | keep polling; do **nothing** with the tasks |
| `true`  | session terminated | read `session_status`, tasks, escalations; promote the summary |

When `final: true`, `session_status` is the **terminal reason** (see §5), never the
raw `"active"`.

---

## 5. Terminal paths — how a session ends

Every terminal path yields `final: true`, all panes reaped, a valid manifest, and
process exit 0.

| How it ends | Trigger | `session_status` |
| --- | --- | --- |
| **Timeout** | `--timeout` expires | `timeout` |
| **Explicit stop** | `agent-team stop --session <uuid>` | `stopped` |
| **SIGTERM** | `kill -TERM <start-pid>` (container/orchestrator stop) | `signal` |
| **Crash + reap** | orchestrator `kill -9`'d → orphan panes survive → you run `agent-team stop` to reap them | `stopped` |

**Always have a stop path.** If you `kill -9` the orchestrator, the auto-approve
teammates are orphaned and keep editing — run `agent-team stop --session <uuid>`
to reap them. `stop` records the terminal event, reaps panes, and lets a
backgrounded run exit 0; the manifest regenerates from the stores regardless.

---

## 6. The result manifest (`logs manifest --format json`)

Top-level envelope (`manifest_version: 2`):

| field | type | meaning |
| --- | --- | --- |
| `manifest_version` | int | pinned schema version (`2`) |
| `session_id` | str | the session id you started |
| `project_path` | str | consumer repo path |
| `playbook` | str \| null | playbook used |
| `session_status` | str | terminal reason when `final`, else raw status |
| `session_stopped` | bool | an `orchestrator_stopped` event was recorded |
| `final` | bool | **the completion flag — see §4** |
| `summary` | str \| null | session summary (null until the S16c hook lands) |
| `members` | list | `{ name, role, persona, cli, status }` |
| `tasks` | list | task records (below) |
| `counts` | obj | task count keyed by derived status |
| `escalation` | list | `{ level, subject, reason }` — surfaced hangs/failures |

Each **task record**:

| field | meaning |
| --- | --- |
| `task_id`, `title`, `input` | task identity + instruction |
| `role`, `assignee` | persona/role and member name (null if unassigned) |
| `status` | `completed` \| `abandoned` \| `blocked` \| `in_progress` \| `pending` (DERIVED) |
| `deps` | task ids this one waits on |
| `output` | task result, else best-effort last mail from the assignee |
| `decision` | `{ decision, decided_by }` from the spawn resolution |
| `next_action`, `artifact_path` | null today (S16c hook) |

**Derived-status note:** `abandoned` = a task was `in_progress` when the session
stopped; `blocked` = a pending task waits on a dep that is missing or not
completed. These are computed at read time, so `counts` here differs from
`status --json`'s raw `task_counts`.

Other formats: `--format jsonl` (one task object per line, envelope dropped) for
streaming into a task store; `--format md` for a human task board.

---

## 7. Safety framing (read before you auto-approve anything)

> **The spawn-approval gate is a resource/audit control, NOT a safety control
> over what a teammate then does.** It governs *whether to spawn*, never *what the
> spawned agent does next.* Once approved, `codex`/`agy` teammates run with
> **auto-approve-all** flags. Your approval decision is therefore a decision to let
> an agent edit the worktree autonomously — gate it on persona, cost, and the
> `isolate_worktrees` guarantee, not on a belief that a later prompt will stop it.

- **Containment is the real safety boundary.** With `isolate_worktrees: true`,
  each `workspace-write` teammate edits only its own worktree; the main checkout is
  untouched until the lead/reviewer merges. Do not run unattended without it.
- **Quota/auth is shared.** One `~/.claude` / `~/.codex` is shared quota and a
  same-session-id collision risk. True parallel autonomous sessions need isolated
  auth dirs.

---

## 8. Exit codes & error handling

| command | exit | meaning |
| --- | --- | --- |
| `status` | `0` | ran, team healthy |
| `status` | `2` | ran, team **unhealthy** (dead teammate, escalation) |
| any | `1` | the command itself failed (bad session id, usage error) |

Distinguish `2` (a team problem you may escalate) from `1` (you called it wrong).
On `1`, fix the call; do not retry verbatim.

---

## 9. Minimal end-to-end skeleton

```bash
SID="myproj-$(uuidgen)"
agent-team start --project /repos/myproj --session "$SID" \
  --context "POST /refunds API 추가. TEAM.md 준수. pytest 전부 통과 후 마무리." \
  --autonomous --timeout 1800 &
START_PID=$!

# Approve spawns as they appear (loop until the session ends):
while kill -0 "$START_PID" 2>/dev/null; do
  PENDING=$(agent-team approvals list --session "$SID" --json)
  ID=$(printf '%s' "$PENDING" | jq -r '.pending.request_id // empty')
  [ -n "$ID" ] && agent-team approvals approve --session "$SID" --id "$ID" --by hermes
  sleep 2
done

# Read the result ONLY now that the run has ended:
MANIFEST=$(agent-team logs manifest --session "$SID" --format json)
[ "$(printf '%s' "$MANIFEST" | jq -r '.final')" = "true" ] || agent-team stop --session "$SID"
printf '%s' "$MANIFEST" | jq '{status: .session_status, counts}'
```

Replace the poll loop with an event-driven `logs tail --follow` consumer if you
prefer; the contract is identical. The persona/cost policy that decides
approve-vs-deny is **yours** — agent-team only exposes the mechanism.
