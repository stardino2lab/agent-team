# S13+ Next-Phase Roadmap — agent-team

> Status: **PLAN — rev2, 3-expert reviewed** (architecture / delivery / safety,
> all verified against code). Supersedes the loose "9 improvement ideas" with a
> chunked, gated roadmap. Authored 2026-06-19. Companion to
> `docs/s11-multi-cli-plan.md` (D1–D12 decisions) and `PROGRESS.md`.

## Plan review outcome (3 experts, 2026-06-19)

A 3-expert review (architecture soundness / delivery sequencing / autonomy +
safety) verified every load-bearing claim against the code. Verdicts:
**Architecture = sound-with-fixes**, **Delivery = approve-with-changes**,
**Safety = NOT safe to run autonomously in the original ordering**. rev2 folds in
all findings. The five BLOCKING corrections (each was a claim that did not match
the code):

1. **Retry has no wake to fire on (S14b).** Both `FileWatcher`s are edge-triggered
   (`_watcher.py`) and `start.py`'s loop never calls `run_once`; a failed spawn —
   exactly when no further file activity comes — would never retry. → S14b now
   uses **one short-lived timer, scheduled only while retries are outstanding**;
   `retries.jsonl` moves **out of `approval/`** so it doesn't self-wake the watcher.
2. **Manifest `role` has no source (S16a).** `Member.role` is only `lead`/`teammate`
   and `Persona` has **no role field**. → use `member.persona` as the role label.
3. **Manifest `decision` has no source (S16a).** `spawn_approved` payload is only
   `{request_id, persona}`; `decided_by` lives in `resolutions.jsonl`; "lead notes"
   exist nowhere. → derive `decision` from a **events↔resolutions.jsonl join**.
4. **Spawn approval is not a safety control (S18).** It gates *whether to spawn*,
   not *what the teammate does*; teammates run auto-approve-all in the project root
   with no sandbox. → **containment (S17) moves before autonomy (S18)**; codex runs
   a sandboxed profile in autonomous mode; agy (no sandbox flag) is excluded from
   unattended runs or confined to a container/VM.
5. **~6 liveness paths hang until timeout (S18).** dead pane / dropped kickoff /
   `wait_for_event` stall / `max_teammates` / unresolved approval all hang with no
   human. → **S14 (status/health/retry) moves before S18**; `--timeout` is
   mandatory in autonomous mode and the terminal path `kill_session`s every pane.

Plus latent bugs surfaced and now scheduled (S14d): `event_log.read` crashes on a
torn trailing line (any crash corrupts the whole log); `wait_for_event` `since`
uses second-granularity `<=`, so two events in the same second drop one →
silent lead stall. Both are fixed before the lead becomes the sole driver.

## Context — why this phase

agent-team is a mature, **Windows-native** multi-agent orchestrator (S10 E2E
passed, S11a/b/c landed, S12a agy-teammate code-complete; **248 tests, ruff
clean**). The next phase grows it from a single-machine Windows tool into a
**cross-platform, multi-LLM team engine** that an upstream orchestrator
(**Hermes**) can drive by difficulty and read back as structured records.

The work was scoped from 9 improvement ideas. Expert review mapped each to the
existing architecture and found:

- The codebase is already cross-platform **except one file** — `psmux_backend.py`.
  psmux and tmux are **~100 % command-compatible** (only the `new-session` /
  `split-window` command separator differs: psmux `-- CMD` vs tmux trailing
  `CMD`). So OS independence is a **low-risk abstraction**, not a rewrite.
- Recording (events/mailbox/tasks/session) and the internal team (personas) are
  **already built**. The gaps are: a **standardized projection** for Hermes, and
  **operational stability** (status/health/retry/escalation).
- **"Gemini" = `agy`** (Antigravity, Claude-Code-derived). Confirmed with the
  user: no separate Google `gemini` binary; finish/verify the existing `agy`
  worker. Use `agy` everywhere.
- **Hermes** does not exist in this repo and is **out of scope to build here**;
  this repo only exposes the clean surface Hermes consumes (manifest + triage +
  escalation). Difficulty routing is a Hermes-side decision; agent-team supplies
  facts, not the classifier.

**Track order (user-directed + safety reorder):** OS independence (psmux↔tmux)
**first**, riding the command-compatibility. Then — per the safety review —
**operational stability (S14) and containment (S17) come BEFORE autonomy (S18)**:
you cannot safely let an unsandboxed, auto-approve team run unattended until
failures are detectable (S14) and blast radius is contained (S17). agy gate-only
verification (S15a) runs **first of all** (no code, closes a paid milestone).

### Idea → milestone coverage

| # | Idea | Where | Note |
|---|------|-------|------|
| 1 | OS 독립화 (Linux) | **S13** (FIRST) | TerminalBackend abstraction + tmux |
| 2 | 멀티 LLM (agy) | **S15** | finish agy teammate + lead |
| 3 | Hermes 상위 오케스트레이터 | **S16** + **S18** | boundary = CLI + manifest; S18 makes it autonomous (Hermes-approved, headless) |
| 4 | 난이도 라우팅 | S16d + S14c | agent-team exposes capacity (triage) + post-hoc escalation only; difficulty decision is 100% Hermes-side (no pre-flight score) |
| 5 | 기록 포맷 표준화 | **S16a** | result manifest (projection) |
| 6 | 내부 팀 구조 강화 | exists | minor: `agy-tester` persona (S15c) |
| 7 | 상태 추적/감사 로그 | **S14** | status/health/retry/escalation |
| 8 | Hermes 연결 (output→input) | **S16** | manifest = agent-team output |
| 9 | 운영 안정성 | **S14** | health/retry/escalation |

---

## Milestone map (recommended execution order, rev2)

Re-sequenced per the delivery + safety reviews. The marker shows *why* each is
placed where it is. Numbers are milestone ids (not execution rank — read top to
bottom for order).

```
 1. S15a  agy teammate live gates (G1 + helper)   [NO code]   ← free; closes a paid milestone
 2. S13a  TerminalBackend abstraction + Windows-parity refactor  ← invisible on Windows; foundation
 3. S14a  health model + `agent-team status`                    ← highest ops ROI; debug tool for all that follows
 4. S13b  TmuxBackend + factory  (+ Linux mock CI job)
 5. S13c  Linux/macOS live verification (G3/G4)                 ← first cross-platform payoff
 6. S14b  spawn retry + recovery (timer-while-pending)
    S14c  escalation ladder
    S14d  crash/race hardening (event_log torn-line, wait_for_event granularity)
 7. S16a  result-manifest projection (`logs manifest`)          ← on the autonomy critical path
    S16b  session-end manifest cache (+ regenerate-from-stores fallback)
 8. S17   worktree isolation / containment                      ← MOVED BEFORE S18 (blast-radius control)
 9. S18a  external-approver interface (Hermes resolves spawns)
10. S18b1 detach + exit code + `stop`
    S18b2 terminal-state + mandatory `--timeout` + kill-all-panes
    S18b3 crash-safe terminal manifest (signal handler + orphan-pane reaper)
11. S18c  headless autonomous E2E (G5)                          ← the autonomy proof
12. S15b  agy lead (MCP-hosting spike → drop-in)                ← cost/optionality, off critical path
    S15c  cost-aware role→CLI (allowed_personas + agy-tester)
    S16c  lead result/summary hooks      } deferred — consumer-less Hermes surface;
    S16d  triage / capability descriptor } build only when Hermes is real
    S16e  Hermes contract doc            } needs Hermes + the full S18 stack
```

**Critical path to "autonomous under Hermes on Linux":**
S13a→S13b→S13c → S14a→S14b→S14d → S16a→S16b → S17 → S18a→S18b→S18c → S16e.
Off the critical path (value-add, parallelizable): S15b/c, S16c/d, S14c.

> **Why S18 exists, and why S14+S17 precede it.** S16 solves the *output handoff*
> (Hermes reads the manifest); S18 solves the *invocation/control* path. Code
> review found three control blockers — (A) spawns are gated by a **human TUI
> approval** (`spawn_approval.approve(decided_by="user")`, no non-human path) →
> unattended deadlock at first spawn; (B) `agent-team start` **blocks forever**
> (`--no-block` is a hidden seam that tears down the watcher) → no daemon/completion
> contract; (C) lead/teammates are **interactive panes** with unverified headless
> behavior. **But** the safety review showed the approval gate is *not* a safety
> control over teammate actions: once spawned, codex/agy teammates run
> **auto-approve-all in the project root with no sandbox**. So liveness (S14) and
> containment (S17) are **prerequisites** of autonomy (S18), not later polish.
> **S16e (the Hermes contract) depends on the full S18 stack.**

Each milestone keeps the repo's conventions: **pytest** for pure logic
(injecting `PsmuxBackend(mock=True)` / seeded stores), a **`tests/manual/sNN-*.md`
gate checklist** for anything that spends tokens or needs a live pane, a
**PROGRESS.md** entry, and **ruff clean**.

---

## S13 — Cross-platform terminal backend (FIRST)

**Goal:** run agent-team on Linux/macOS via `tmux`, keep Windows/`psmux` working,
selected automatically with an env override. Mechanism: a `TerminalBackend`
abstraction that makes the two interchangeable (they already are, bar one argv).

### S13a — Abstraction + Windows-parity refactor (NO behavior change)

New module `src/agent_team/terminal_backend.py`:

- `TerminalBackend` **Protocol** (`@runtime_checkable`) with exactly today's
  methods: `new_session`, `split_pane`, `send_keys`, `kill_pane`, `kill_session`,
  `list_panes`, `capture_pane`, `pipe_pane`, `recorded_calls`, plus a `name`
  property (`"psmux"`/`"tmux"`). Protocol over ABC — `PsmuxBackend` already has
  the exact shapes; zero inheritance churn; keeps `mock=True` doubles valid.
- Move shared value types (`PaneInfo`, `RecordedCall`), the pane-id regex
  `%[0-9]+` + `_validate_target` (identical for tmux `#{pane_id}` = `%N`), and a
  shared `MockTerminalBackend` (extracted from `PsmuxBackend`'s mock state) here —
  guarantees mock parity so existing argv tests stay valid.
- Neutral exception hierarchy: `TerminalBackendError` (base),
  `BackendNotFoundError`, `BackendCommandError`. Keep `PsmuxNotFoundError` /
  `PsmuxCommandError` as **aliases** for one milestone so catch-sites
  (`cli/start.py`, `cli/attach.py`, `mcp_server.py`) don't break on a flag day.
- `make_terminal_backend(*, mock=False) -> TerminalBackend` factory: `mock` →
  `MockTerminalBackend`; else `AGENT_TEAM_BACKEND` env (`psmux`|`tmux`) if set;
  else `sys.platform == "win32"` → psmux, otherwise tmux. **Selection lives in
  one place.** Repoint the 3–4 construction sites (`cli/start.py`,
  `cli/attach.py`, `mcp_server.py`) to the factory — still psmux on win32, so
  **byte-identical on Windows**.
- **Fold in submit-keys platform defaulting here.** `CliSpec.teammate_submit_keys`
  (codex `("Tab","Enter")` is Linux-observed; Windows TBD per
  `tests/manual/s11b-teammate-hardening.md` §D11b) is currently env-overridable via
  `AGENT_TEAM_SUBMIT_KEYS_<CLI>` with no `sys.platform` branch. When the factory
  lands `sys.platform` selection, make the codex submit-keys default
  platform-conditional in the same one place (env still wins), so Linux no longer
  needs the env var.

Seal the abstraction leaks (all behavior-preserving on Windows):

- `Member.backend` literal `"psmux"` (`orchestrator.py` two sites) → `backend.name`.
  **Do not rename the on-disk `Session.psmux_session` JSON key** — old
  `session.json` must keep loading (`_member_from_dict` reads verbatim).
- Centralize launch-line quoting into `quote_pane_arg(value, *, shell_family)`:
  `posix` → `shlex.quote`; `windows` → current double-quote wrapping. Route the
  `_build_lead_launch_command` quote sites, the codex bootstrap prompt, and the
  `pipe_pane` `cat >> "<path>"` redirect through it. Keep paths `.as_posix()`
  regardless of shell. The set of strings reaching a shell is tiny and fully
  controlled (exe, a few flags, 2–3 abs paths, one bootstrap) — **no user
  free-text on a pane command line** (the dangerous multi-line system prompt is
  delivered via file, never the shell — preserve that invariant).

**Files:** new `src/agent_team/terminal_backend.py`; edit `psmux_backend.py`
(keep real psmux argv incl. the `--` separator; move shared bits out),
`orchestrator.py`, `teammate_runner.py`, `cli/_helpers.py`, `cli/start.py`,
`cli/attach.py`, `mcp_server.py`.

**Verify (Gate G1):** Windows suite green (≥248), ruff clean; `s9-claude-lead.md`
+ `s11c-codex-lead.md` manual smoke unchanged. Parametrize existing argv tests
over the shared mock; add `test_terminal_backend_factory.py` (mock→mock
regardless of platform; env override; platform default via monkeypatched
`sys.platform`; missing exe → `BackendNotFoundError`).

### S13b — TmuxBackend + factory default

- `TmuxBackend(TerminalBackend)` overriding **only** the `new-session` /
  `split-window` command assembly (drop psmux's `--`; tmux takes the command as a
  trailing arg). Everything else — `send-keys -l` + separate bare `Enter`,
  `capture-pane -p`, `pipe-pane -o`, `list-panes -F #{pane_id}`, `kill-*` — is
  identical and inherited.
- Factory default win32→psmux else tmux, `AGENT_TEAM_BACKEND` override (the test
  seam to force tmux on the Windows CI box under the mock).
- **Add a Linux CI job** (review gap): `ubuntu-latest` running the pytest suite
  with `AGENT_TEAM_BACKEND=tmux` under the mock — no real tmux needed, cheap, and
  the only recurring guard against a future edit silently re-breaking the tmux
  path (the new cross-platform value prop otherwise has *zero* recurring signal).
- Retarget "Windows-native" docs (`__main__.py`, `__init__.py`, `README.md`,
  `docs/architecture.md`) → "cross-platform (Windows via psmux, Linux/macOS via
  tmux)". Optional cosmetic: internal attr `psmux`→`terminal`, add `--no-panes`
  alias keeping `--no-psmux`.

**psmux ↔ tmux mapping** — **two** forks, not one (review correction):

| op | psmux | tmux | fork? |
|----|-------|------|------|
| new session | `new-session -d -s N [-c CWD] -- CMD` | `… [-c CWD] CMD` (trailing) | **command separator** |
| split | `split-window … [-p N] -- CMD` | `… [-p N\|-l N%] CMD` | **separator + `-p`→`-l` on tmux ≥3.4** |
| send literal / Enter | `send-keys -t T -l KEYS` / `send-keys -t T Enter` | identical | no |
| kill / list / capture / pipe | `kill-pane`/`kill-session`/`list-panes -F #{pane_id}`/`capture-pane -p`/`pipe-pane -o` | identical | no |

> **`-p` is a real second fork.** `split_pane` passes `-p <size_percent>`
> (`psmux_backend.py`); tmux **3.4 removed `-p`** in favor of `-l N%`. `TmuxBackend`
> must branch the size flag on tmux version (or pin a min version and document it),
> not treat split as a pure separator swap.

> **Hidden coupling — pane-id discovery is stateful, not argv.** `new_session` /
> `split_pane` don't parse their own output; they call `list_panes` and diff the
> pane set (`after - before`), asserting "exactly one new pane." `TmuxBackend`
> inherits this multi-command logic unchanged — it breaks if the target session
> already has multiple panes or a rename hook fires. The S13c gate **must** split
> into an existing multi-pane session, not just a fresh one.

**Verify (Gate G2):** new `test_tmux_backend.py` asserts tmux argv per method
(both forks: separator **and** `-p`→`-l`); full suite green with
`AGENT_TEAM_BACKEND=tmux` forced under the mock on the Windows runner + the new
ubuntu-latest CI job. Windows still defaults to psmux.

### S13c — Linux/macOS live verification

New `tests/manual/s13-tmux-linux.md` mirroring `s9-claude-lead.md`:

- Preconditions: Linux box, `tmux -V` ≥ pinned min (verify `-p` split sizing and
  `-o` pipe-pane), `claude --version`, `pip install -e .`, `pytest -q` green,
  **started from an activated venv** (pane inherits orchestrator PATH/venv).
- Steps: `AGENT_TEAM_BACKEND=tmux agent-team start --project . --session s13-test`
  → `tmux attach`; verify lead pane runs claude, MCP `agent-team` lists under
  `--strict-mcp-config`, system-prompt content present; approve one spawn in TUI;
  confirm `teammate_ready`, `transcript.log` written by pipe-pane, the `-l`+Enter
  kickoff actually submitted, mail delivered; Ctrl-C → stop event. macOS optional
  second pass.

**Gate G3:** Linux E2E PASSED. **G4 (optional):** macOS E2E PASSED. Record in
PROGRESS.md in the existing style.

**Risks:** tmux 3.4+ deprecates `split-window -p` for `-l P%` (pin min version;
branch in `TmuxBackend` only if needed) · exotic pane shell (fish) quotes
differently (`shlex.quote` targets sh/bash/zsh; document fish unsupported) · the
`--` separator is the one real behavioral fork (explicit per-backend argv test +
live gate) · keep psmux-named exception aliases one milestone.

---

## S14 — Operational stability

**Goal:** make "who did what, and is it still alive?" visible and recoverable —
without violating the event-driven, no-polling-loop architecture
(`project_loader.py` forbids lead/teammate `test -f` loops). A **user-invoked,
one-shot** CLI command that reads files once and exits is allowed.

### S14a — Health model + `agent-team status`

New `src/agent_team/health.py` (pure, read-only, injectable deps): `derive_health`
+ `last_activity` + `SessionHealth` dataclass. Health is **derived at read time**,
no new persisted field, from signals the system already writes:

Precedence is evaluated **top-down** — `starting` grace short-circuits **before**
the `dead` pane check (review fix: during the spawn race the member is persisted
with a `pane_id` before the pane appears in `list_panes`, so an early `dead` check
would false-positive):

1. `error` — `member.status == "error"` or an unrecovered `error` event for the
   member's `request_id`.
2. `starting` — `pending`/`starting` within a spawn grace window (~90 s).
   **Checked before `dead`.**
3. `dead` — `member.pane_id` set, past grace, but absent from
   `backend.list_panes(session)` (pane crashed; strongest signal, no timestamps).
4. `stale` — pane alive + ready-marker present, but `now - last_activity >
   stale_after` (default ~10 min, configurable). The "hung teammate" case.
5. `healthy` — pane alive, marker present, fresh.

`last_activity(member)` = **max** of (newest `events.jsonl` ts naming the member)
and (`teammates/{name}/transcript.log` mtime) — catches a teammate busy on a long
build that hasn't mailed (the D6 preamble tells teammates *not* to mail while
working, so transcript mtime is the only heartbeat during a long quiet task).
**No heartbeat writer, no timer thread, no `test -f` loop** — freshness is a side
effect of work already recorded. **Gate caveat:** `pipe_pane`'s `cat >>` buffering
is unverified, so the live gate must confirm transcript mtime **advances during a
long silent operation** — else a busy teammate reads as false `stale`.

New `src/agent_team/cli/status.py` (mirrors `cli/logs.py`): `agent-team status
--session <id> [--json]` prints per-member CLI/status/pane/health/last-activity +
task counts + pending approval; exits non-zero if any member is `dead`/`error`.
Optional MCP `get_status` tool so the **lead** can self-diagnose in one call
(stays low-token).

**Verify:** pytest truth-table for `derive_health` (every state incl. the
starting-before-dead precedence) on seeded sessions; dead-pane detection **and**
transcript-mtime-advances-during-silent-work in a live `tests/manual/s14-status-gates.md`
(**Gate G-status**; mock panes can't model a crashed pane — give it a real gate).

### S14b — Spawn retry + recovery

New `src/agent_team/recovery.py`: pure `backoff(attempts)`, retry-record
read/write (append-only `approval/retries.jsonl`, same pattern as
`resolutions.jsonl`), retryable-vs-hard-stop classifier.

- **Retry does NOT need re-approval.** The `SpawnResolution` already records the
  user's approval of *this persona + prompt*; a transient psmux/launch failure is
  an execution failure of an approved intent. Retries operate on the approved
  resolution, **bounded** (`max_spawn_retries`, default 3) with **exponential
  backoff** (5s/20s/60s cap). Re-approval is required only to change
  persona/prompt or after the budget is exhausted (→ escalation).
- **Re-attempt needs a real wake (review BLOCKING fix).** The original "reconcile
  on the existing `run_once`/`poll_ready` wakes" is unimplementable: both
  `FileWatcher`s are edge-triggered (`_watcher.py`) and nothing fires after a spawn
  fails (no further file activity is coming). So a backoff window with no other
  activity would **never re-attempt**. Fix: a **single short-lived
  `threading.Timer`, armed only while a retry record is outstanding**, that calls
  `run_once` when `next_eligible_ts` elapses (disarmed when none remain). This is
  not a polling loop — it's one timer that exists only between a failure and its
  retry. `retries.jsonl` lives in a **new `recovery/` dir, NOT `approval/`**, so
  writing it doesn't spuriously self-wake the approval watcher.
- **Retryable** (psmux command error, kickoff timeout) vs **non-retryable**
  (`invalid_resolution`, `max_teammates_exceeded` — already-correct hard stops;
  escalate immediately, never retry).
- Persist across detach/attach (`recovery/retries.jsonl`); `attach` reconciles
  outstanding retries and re-arms the timer.

**Files:** `orchestrator.py` (`_spawn_one`/`run_once`/`attach` + timer), new
`recovery.py`. **Verify:** pytest — injected psmux failure retries N× w/ backoff
then errors (with a fake/controllable clock, not real sleeps); the timer fires the
re-attempt with NO other file activity; survives detach/attach; hard-stops don't
retry. Gate `s14-retry-gates.md`.

### S14d — Crash/race hardening (autonomy prerequisite)

Two latent bugs the safety review surfaced; both must be fixed before the lead is
the sole unattended driver (S18):

- **`event_log.read` crashes on a torn trailing line.** `json.loads` is unguarded,
  so a kill mid-append (any crash) leaves a partial last line that makes the
  **entire event log unreadable** — breaking `wait_for_event`, `reconcile_handled`,
  and the manifest projection. Fix: per-line `try/except` that skips a torn final
  line (mirror `read_resolutions`, which already tolerates this).
- **`wait_for_event` misses same-second events.** `format_ts` is second-precision
  and `since` filtering uses `<=`; two events in the same wall-clock second →
  re-arming `wait_for_event(since=last_ts)` filters out the second one → the lead
  waits forever for an event it already discarded. Fix: sub-second timestamps **or**
  `<` semantics + event-id de-dup. Under a human this is a rare nuisance; under an
  unattended lead it is a silent stall.

**Verify:** pytest — torn-line fixture still reads; two same-second events both
delivered across a `wait_for_event` re-arm. No gate (pure logic).

### S14c — Escalation ladder

Detection + event emission only (never auto-spawns beyond the bounded budget —
cost control + preserves the approval invariant). Three rungs, all new event
types on the existing bus (lead sees them via `wait_for_event`/`get_recent_events`
— zero new transport):

1. **teammate** — retries exhausted, or member `dead`/`stale`.
2. **task** — a task sits `in_progress` with no activity past `task_block_after`
   (same staleness derivation).
3. **user** — lead can't resolve / escalation unacknowledged → surfaced
   prominently by `agent-team status` and the TUI. Human is the top rung.

**Verify:** pytest — stale teammate and blocked task each emit one `escalation`;
no auto-respawn past budget. Gate `s14-escalation-gates.md`.

---

## S15 — Multi-LLM completion (agy)

**`agy` is the user's "Gemini" worker.** Claude = reasoning/review, Codex =
implementation, agy = heavy implementation/draft/parallel exploration (unlimited
quota on heavy roles per the cost-asymmetry note). Parallelizable with S13/S14
(it's Windows-native psmux work + gates).

### S15a — agy teammate live verification (NO code)

S12a code is complete; only the **token-spending gates** remain on this box:
- **G1**: `agy --dangerously-skip-permissions` pane accepts the psmux `send_keys`
  kickoff and runs tool calls with no per-command approval / no first-run trust
  prompt — exercises `teammate_runner.py` (input-ready wait → single-line
  kickoff).
- **helper-under-agy**: the `agent-team mail/task/teammate ready` shell helpers
  run under agy on Windows.

Pass = ship (no code change). `tests/manual/s12-agy-gates.md` (G0 already PASS).

### S15b — agy lead (MCP-hosting spike → drop-in)

**Blocked, not a drop-in:** `agy help mcp` → "unknown subcommand: mcp". The lead
must host the agent-team MCP server. First a **spike**: how does agy host MCP
(`.mcp.json`? `agy plugin import claude`? `~/.antigravity/` config)? Once
resolved, the drop-in mirrors S11c's codex pattern: add `supports_lead=True` +
`mcp_format` (likely `"json"` reusing claude's `.mcp.json` machinery) to the agy
`CliSpec`, add an `agy` arm to `_build_lead_launch_command` (the elif chain's
defensive `raise` already anticipates it); `_check_lead_cli_supported` stops
rejecting `lead_cli: agy`. New gate `tests/manual/s12b-agy-lead-gates.md`.

### S15c — Cost-aware role→CLI (minimal, reuse personas)

The **persona already is** the role→CLI binding; no scheduler needed.
- Primary lever (zero new code): a cost-optimized project lists
  `[planner, reviewer, agy-implementer, agy-tester]` in `allowed_personas` —
  Claude for reasoning/review, agy for the heavy implementer/tester. Add a new
  `agy-tester.yaml` persona to round out the heavy set (mirror bundled↔root).
- Optional follow-up: a `role_cli_overrides` map in `config.yaml`
  (`{implementer: agy, tester: agy}`) resolved where the persona's `cli` is read,
  validated against `is_teammate_supported`, default = persona's own `cli`.

**Verify:** pytest — agy-heavy allowlist spawns agy implementer/tester; overrides
validate against the registry. Document the cost recipe.

---

## S16 — Hermes integration & record standardization

**Goal:** "agent-team output becomes Hermes input." **Hermes is out of scope to
build here** — this repo only exposes a clean, versioned surface. Hard rule:
**no second source of truth** — everything new is a **read-only projection** over
`event_log.py` / `tasks.py` / `session.py` / `mailbox.py` / `spawn_approval.py`.

**Boundary:** Hermes shells out to the existing CLI (`agent-team start …`, as a
human does — keeps the process model + language-agnostic) and reads back a
**result manifest** + **triage** command. No programmatic Python entrypoint (would
couple Hermes to this repo's Python/install and bypass the psmux/MCP model).

### S16a — Result-manifest projection

New `src/agent_team/manifest.py` (pure functions, read-only): `build_manifest`
composes existing stores into a **task-centric** `ResultManifest` with the
standardized fields the user asked for, plus a session envelope. Field
derivation:

| field | source (review-corrected) |
|-------|--------|
| `task_id` / `input` / `deps` / timestamps | `tasks/{id}.json` |
| `role` | `task.assignee` → `session.json` member **`persona`** (the persona name *is* the role label; `Member.role` is only `lead`/`teammate` and `Persona` has **no** role field — corrected) |
| `status` | `task.state`, + `blocked` (deps unmet at end) / `abandoned` (in_progress at stop) |
| `output` | preferred: `task_result` event (S16c); fallback: `mailbox/lead.jsonl` from assignee (best-effort; mail has no task linkage) |
| `decision` | **events↔`resolutions.jsonl` join** — `spawn_approved`/`denied` event + `decided_by` from the matching resolution (corrected: `decided_by` is NOT in the event payload; "lead notes" do not exist) |
| `next_action` / `artifact_path` | `task_result` event (S16c); null otherwise |

Envelope: `manifest_version`, session id/path/playbook/status, members[],
`summary`, `tasks[]`, `counts`, `escalation` (from S14c / S16c). CLI:
`agent-team logs manifest --session <id> --format json|jsonl|md` (md = the user's
"task-board markdown"). Added to the **existing** `logs_group` (`cli/logs.py`) —
`logs tail`/`export` untouched. **Backward-compatible:** every new field is
optional → old sessions still project (with nulls).

### S16b — Session-end manifest cache

At the `orchestrator_stopped` hook in `cli/start.py`, also write
`result_manifest.json` into the session dir via `_io.write_json` (atomic). A
**cache of a projection** (disposable, regenerable) — not a new source of truth.

> **Review fix — the cache is a convenience, not the completion contract.** A
> byte-equality test (cache == `render_json(build_manifest)`) is a tautology and
> the on-`finally` write is **skipped on SIGKILL/crash** (S18b3). So the
> authoritative path is: **Hermes regenerates the manifest from the stores**
> (`logs manifest` is a pure projection that works post-hoc, even after a crash).
> The cached file is just a fast read for the common graceful-exit case.

**Verify:** cached file equals the on-demand projection on graceful exit; **and**
`logs manifest` still produces a valid manifest from a session dir whose orchestrator
was killed without writing the cache (the real reliability test).

### S16c — Lead result/summary MCP hooks  · DEFERRED (no consumer yet)

> **Deferred with S16e** (delivery review): these are Hermes-shaped features with
> no consumer to validate the schema against — building them now risks guessing a
> field set that reworks when Hermes is real. S16a/b stand alone as session
> introspection; S16c/d wait until Hermes exists. Kept here for design completeness.

Two new optional MCP tools (additive to the 11) so the lead can emit what Hermes
needs for memory/skill promotion:
- `record_task_result(task_id, output_summary, next_action=None,
  artifact_path=None)` → appends a `task_result` event. `artifact_path` validated
  relative to `project_path` (reject absolute / `..`, reuse `safe_segment`
  philosophy; store a pointer, never read the file).
- `record_session_summary(summary, escalate=False, reason=None)` → `session_summary`
  (+ `escalation_raised` when escalating) event.

Events, not new files (events.jsonl is already ordered/atomic/watched; the TUI
renders generic events → no TUI change). Playbooks get a one-line hint to call
these (guide, not pipeline — lead stays sovereign).

**Guaranteed-minimum manifest (reliability reinforcement).** Because the hooks
are guide-mode (the lead *may* not call them), `build_manifest` must always
produce a usable record from **task + event state alone** — `status`/`role`/
`input`/`decision` derive from the stores regardless of lead cooperation; the
hooks only *enrich* (`output`/`next_action`/`artifact_path`/`summary`). So Hermes
always gets a structured manifest even if the lead emits nothing; hook-populated
fields are best-effort on top, never a precondition for a valid manifest.

### S16d — Triage / capability descriptor (routing support)  · DEFERRED (no consumer yet)

> Deferred with S16c/S16e (same reason — no Hermes to validate the descriptor shape).

`agent-team triage --project … --playbook … [--task "…"]` — **does not start a
session.** Loads config + playbook + persona registry, returns a machine-readable
capability/cost descriptor: `playbook`, `mode`, `allowed_personas[{name,cli,role}]`,
`max_teammates`, `estimated_parallelism`, `requires_approval`, `supported_clis`.
Reuses `handle_list_personas` filtering — cheap, side-effect-free, safe for Hermes
to call per task. **This is agent-team's only "routing support"**; the
difficulty *decision* (easy→Hermes / medium→worker / complex→agent-team /
ambiguous→user) stays entirely in Hermes. The escalation channel (S14c/S16c) is
the "this is too big, escalate" report Hermes reads back.

> **Explicit limitation (idea #4).** triage reports the team's **capacity**
> (personas, parallelism, supported CLIs), **not the task's difficulty**.
> agent-team gives Hermes **no difficulty score and no cheap pre-flight "too big"
> signal** — the only over-scope signal (`escalation`) arrives *after* a session
> has already started and spent tokens. All difficulty judgment is Hermes-side by
> design. A cheap pre-flight estimate (an LLM call inside triage) would be a
> *new*, separately-scoped capability, not part of this plan.

### S16e — Hermes contract doc (deferred — needs Hermes + S18)

`docs/hermes-integration.md` freezing the manifest/triage schema as the contract,
with a worked "shell out → read manifest → promote summary" example + a manual
E2E checklist. **Only this phase needs Hermes to exist** — S16a–d are
independently valuable as better introspection over sessions agent-team already
runs, so don't freeze the schema (`manifest_version`) until there's a consumer.

**Verify:** pytest — `build_manifest` across completed/aborted/blocked/no-hooks
cases; golden-string render tests (json/jsonl/md); triage descriptor equals config
+ creates no session dir; `artifact_path` traversal rejection; pre-S13 session
fixture → valid manifest with nulls. Gates `tests/manual/s16*.md`.

---

## S18 — Unattended/headless operation (PREREQUISITE for autonomous Hermes)

**Goal:** let agent-team run end-to-end **with no human at the terminal**, driven
and resolved by an upstream Hermes. Closes the three control-path blockers found
in code review. **S16e depends on this** — without it, the "Hermes shells out and
walks away" story deadlocks at the first spawn.

**Approval model — Hermes is the approver (user-chosen).** agent-team does **not**
gain an internal auto-approve policy; it exposes the *mechanism* and Hermes (the
upper orchestrator) owns the decision. Small change: `SpawnApproval.approve/deny`
already take `decided_by` — the human TUI is just one caller; Hermes becomes another.

> **CRITICAL safety framing (review BLOCKING #4).** The spawn approval gate is a
> **resource/audit** control, **not a safety control over teammate actions**. It
> approves *whether to spawn*, never *what the teammate then does*. Once spawned,
> codex/agy teammates run with **auto-approve-all** flags
> (`--dangerously-bypass-approvals-and-sandbox` / `--dangerously-skip-permissions`)
> in the **project root** (`teammate_runner.py`) — editing files, running shell and
> git with **zero per-action brake**. Replacing the human approver with Hermes
> removes the last human who reads spawn intent, but the per-action permissions
> were already bypassed by design. **Therefore autonomy requires containment at the
> teammate boundary (S17), not just approval at the spawn boundary.** Hence the
> reorder: **S17 (worktree isolation) + S14 (liveness) ship BEFORE S18.** Hard
> preconditions of any unattended run:
> - each `workspace-write` teammate runs in an **isolated `git worktree` cwd** (S17)
>   so a runaway can't corrupt the main checkout;
> - codex uses a **sandboxed profile** (`--sandbox workspace-write` + approval
>   policy) in autonomous mode instead of the bypass flag; **agy has no sandbox
>   option** → keep agy teammates **out** of unattended Hermes sessions, or run the
>   whole session inside a **container/VM**;
> - network/destructive-op containment lives **outside** this Python (OS sandbox /
>   container / firewalled cwd) — stated as a precondition, not a residual risk.

### S18a — External-approver interface

- **Notify:** Hermes must learn a spawn is pending without polling. Reuse the
  existing `spawn_requested` event (already emitted in `request_spawn`) — Hermes
  watches it via `agent-team logs tail --follow` / a manifest read, or a new thin
  `agent-team approvals --session <id> [--watch] [--json]` that lists/streams
  `approval/pending.json`.
- **Resolve:** new `agent-team approve --session <id> --request <apr-id> [--deny]`
  CLI calling `SpawnApproval.approve/deny(decided_by="hermes")`. The resolution
  lands in `resolutions.jsonl` exactly as a TUI approval would — the orchestrator
  `run_once` path is unchanged, so the spawn proceeds identically. `decided_by`
  attributes the approver in the audit trail (human vs hermes).
- **Invariant preserved:** every spawn is still *resolved by an approver* before
  it runs — the gate isn't removed, the approver is just allowed to be a program.
  The TUI human path stays the default; external-approver is opt-in (Hermes simply
  calls `approve`; optionally a `config.yaml: approver: hermes` to hide the TUI
  modal and surface a clear "awaiting external approval" state instead).

**Files:** new `src/agent_team/cli/approve.py` (+ `approvals` list/watch); reuse
`spawn_approval.py` unchanged. **Verify:** pytest — `approve(decided_by="hermes")`
drives a spawn with no TUI; `resolutions.jsonl` attributes hermes. Gate
`tests/manual/s18a-external-approver.md`.

### S18b — Daemon run mode + completion contract (split into 3, per delivery review)

Today `agent-team start` blocks forever (foreground loop, Ctrl-C only) and the
only `--no-block` flag is a hidden test seam that **tears down the watcher** in
`finally`. Hermes needs start-and-walk-away with a clean terminal signal. This is
**three** independently-reviewable chunks, not one:

**S18b1 — Detach + exit code + `stop`.** A supported run mode whose lifecycle does
**not** route through the `finally` that tears down the watcher. `start` exits with
a meaningful **exit code** (0 success / non-0 failure). New `agent-team stop
--session <id>` (graceful) emits `orchestrator_stopped{reason:"stopped"}`.

**S18b2 — Terminal-state + mandatory timeout + kill-all-panes.** Define session
terminal states and make `--timeout <dur>` **mandatory in autonomous mode** — the
safety review showed timeout is the *primary* liveness backstop for ~6 hang paths
(unresolved approval, `wait_for_event` stall, dropped kickoff, dead teammate,
`max_teammates`), not a secondary net. On any terminal transition the path
**`kill_session`s every pane** so a stuck teammate stops draining the shared quota.
Completion is an **explicit `orchestrator_stopped{reason}`** event
(`completed`/`timeout`/`stopped`/`error`); the manifest carries `session_status` +
a `final` boolean, and **Hermes must act only on `final=true`** (closes the
mid-flight-read hazard: `logs manifest` is callable any time and would otherwise
show in-progress tasks as the answer).

> "All tasks completed + lead idle" is **not** a reliable done-signal on its own —
> tasks are created by the lead mid-run, and a guide-mode lead emits no "I'm done"
> record unless it calls `record_session_summary` (S16c, deferred). So the honest
> completion contract is **timeout- or explicit-stop-driven**, with task-state as a
> hint, not the trigger.

**S18b3 — Crash-safe terminal manifest + orphan reaper.** "Guaranteed manifest even
on abnormal exit" is **not** achievable via `finally` (SIGKILL/power-loss skip it;
startup-phase failures bypass it). Real fix: (a) Hermes regenerates the manifest
from the stores post-hoc (S16a is a pure projection — works after a crash); (b) a
best-effort terminal write from a **signal handler**, not only `finally`; (c) an
**orphan-pane reaper** — on `attach`/restart, detect and `kill_session` panes left
running by a dead orchestrator (today nothing reaps them; auto-approve teammates
keep editing headless). Depends on S14d's torn-line fix so a crash-truncated
`events.jsonl` is still readable.

**Files:** `cli/start.py` (lifecycle/exit-code/timeout, signal handler), new
`cli/stop.py`, `orchestrator.py` (terminal-state detection, kill-all-panes, orphan
reaper, manifest write). **Verify:** pytest per chunk — exit codes; terminal-state
+ timeout fires kill-all; `final` flag gating; a session dir whose orchestrator was
hard-killed still yields a valid manifest via `logs manifest`. Gates
`tests/manual/s18b-daemon-lifecycle.md`.

### S18c — Headless gate

The lead/teammates run as **interactive** CLI panes (send_keys-driven). Verify
this actually works unattended: claude/agy/codex interactive in a **detached tmux
pane on a headless Linux box with no controlling TTY**, external approver
resolving spawns, completion contract firing. Extends S13c.

**Verify:** new `tests/manual/s18c-headless.md` — full E2E with zero human
interaction (Hermes-role script drives `start` + `approve` + reads manifest), run
on a headless Linux host. **Gate G5:** headless autonomous E2E PASSED.

**Risks:** interactive CLIs may require a PTY even when detached (tmux allocates a
pty per pane — verify each CLI is happy with it) · "terminal session state" is
fuzzy for a guide-mode lead → timeout is the *primary* mechanism, not a backstop
(S18b2) · **external-approver removes the human safety brake — this is NOT
mitigated by spawn-level approval** (it gates spawning, not teammate actions; see
the CRITICAL framing above). The real mitigation is **containment (S17) + sandboxed
codex + agy-excluded/VM**, which is why they precede S18. Concurrency: globally-
unique session ids are required in autonomous mode (the `project.name` sid default
collides on Hermes retries), and the cross-process `approve` CLI needs a **file
lock on `approval/`** (the in-process `RLock` doesn't cover a separate process).

---

## S17 — Conflict hardening / containment: worktree isolation (BEFORE S18)

> **Reordered (safety review): S17 now precedes S18.** It is not just multi-writer
> conflict hardening — it is the **blast-radius control** that makes unattended
> autonomy defensible. An auto-approve teammate with no isolation can corrupt the
> live checkout; worktree isolation is the cheapest real containment (the runner
> already parameterizes `cwd`). Still opt-in for attended runs; **required** for
> autonomous (S18) runs.

The coordination layer is race-safe (task claim lock, `max_teammates`, single
pending approval, `RLock` on member mutation, atomic `session.json`). The
remaining gap is **filesystem-level**: two implementer teammates editing the same
file in one working tree (the task lock guards tasks, not files), and — under
autonomy — an unsupervised teammate writing anywhere in the project root.

- Now (cheap): document the convention — lead assigns non-overlapping file scopes;
  optional advisory `paths` field on tasks; reviewer serializes integration.
- The real fix (this milestone, **opt-in** behind `isolate_worktrees: true`,
  scoped to implementer-class personas): give each such teammate its own
  `git worktree` under the session dir as `cwd` (the runner already
  parameterizes `cwd`), create on spawn / prune on shutdown
  (`handle_shutdown_teammate`); lead/reviewer integrates via merge.
- Fallback if worktrees prove heavy on Windows: a single-writer **write-lease**
  (≤1 `workspace-write` teammate active), analogous to single-pending-approval.

**Risk:** Windows path length, file locks, psmux/tmux `cwd` interaction — needs a
live gate `tests/manual/s17-worktree-gates.md` (G6: two implementers edit the same
file in isolated trees; merge; prune on shutdown; **predictable failure semantics /
no zombie pane**, carried over from the old s11-plan G6).

---

## Cross-cutting conventions

- **Naming:** `agy` (Antigravity), never `gemini`, in code/tests/docs. If a real
  Google `gemini` binary is ever wanted it's a *new* registry entry + personas +
  gate set — the S15c persona/allowlist approach generalizes to N CLIs.
- **Milestone style:** S-numbers, D-decisions, G-gates; pytest for pure logic
  (mock backend + seeded stores), `tests/manual/sNN-*.md` for token/live checks,
  a PROGRESS.md entry per landed slice, ruff clean, additive test counts.
- **Invariants to preserve:** lead/teammate CLI decoupling (lead names only a
  persona; runner reads CLI flags from the registry) · low-token lead (D6
  preamble: no file reads/edits/polling) · MCP-client isolation · event-driven,
  no `test -f` loops · **approval-gated spawns** (S18 keeps the gate; it only lets
  the *approver* be a program — Hermes — instead of a TUI human, attributed via
  `decided_by`) · no second source of truth.

## Dependencies & independence (rev2)

- **S15a** is independent and **first** — no code, closes the paid agy milestone,
  surfaces any G1 trust-prompt bug now. (Live token gate — runs on the user's box.)
- **S13** is FIRST among code work (user-directed). S13a is invisible on Windows.
  S13c needs a real Linux box (live gate).
- **S14** is independent of S16 (pure local stores) but is a **prerequisite for
  S18** (you can't run unattended what you can't observe/recover). Pull S14a early
  — it's the debug tool for everything after.
- **S15b/c** are off the critical path (cost/optionality); S15b is externally
  blocked on the agy-MCP spike (could be L).
- **S16a/b** are on the autonomy critical path (manifest = completion artifact);
  **S16c/d/e are deferred** until Hermes is a real consumer.
- **S17 (containment)** now **precedes S18** — it is the blast-radius control that
  makes autonomy safe, not optional polish.
- **S18** (autonomous/headless) is the **prerequisite for unattended Hermes** and
  for S16e. Requires S13 (tmux/detached) + S14 (liveness) + S17 (containment) +
  S16a/b (manifest). **Not needed at all if a human stays at the TUI.**

**Concurrency hygiene (all autonomous milestones):** require globally-unique
session ids (reject the `project.name` default for Hermes — mint a uuid suffix);
file-lock `approval/` for the cross-process `approve` CLI; document that true
parallel sessions need isolated auth dirs (one `~/.claude`/`~/.codex`/`CODEX_HOME`
is shared quota + a same-sid collision risk). **Config schema:** add a
`config_version` to `config.yaml` as it gains `role_cli_overrides` (S15c),
`isolate_worktrees` (S17), `approver` (S18) — same forward-compat discipline as the
preserved `Session.psmux_session` key.

## End-to-end verification (per milestone)

1. `pytest tests/ -q` green (additive count), `ruff` clean — the primary gate.
2. The milestone's `tests/manual/sNN-*.md` checklist run live on the target box
   (Windows for S14/S15/S16/S17; **Linux for S13c**), token checks separated from
   free checks, outcome recorded in PROGRESS.md.
3. Cross-platform smoke: S13 re-runs `s9-claude-lead.md` (Windows) **and**
   `s13-tmux-linux.md` (Linux) to prove parity.
