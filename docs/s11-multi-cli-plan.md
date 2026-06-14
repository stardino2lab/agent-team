# S11 Plan — Multi-CLI lead/teammate (cost-aware role allocation)

Plan doc for the post-S10 question: *can other AIs (Codex, Gemini/Antigravity) be used as
lead or teammate, and is MCP usage possible?* Verified by running the real binaries on this
Windows machine (not just docs). Implementation follows after the expert gate.

Now grounded in the **S10 manual E2E (2026-06-15, PASSED)** — the first real-token run — and
a 3-expert review of the lead's behavior. That review folded two extra workstreams into S11:
**$20-lead token hardening** (D6/D8/D9 — the cost-aware premise made structural) and
**observability/reliability hardening** (D10 transcripts, D11 kickoff readiness). See
*Empirical validation* below and the *Phasing* split (S11a/b/c).

## Context (why)

The user runs on an enterprise setup with very different per-CLI economics:

| CLI | Plan cost | Quota | Verified on this machine |
|-----|-----------|-------|--------------------------|
| Claude (`claude`) | ~$20/mo | **limited** (caps fast) | ✅ v2.1.175 |
| Codex (`codex`) | ~$440/mo | high but expensive | ✅ v0.139.0 |
| Gemini / Antigravity | ~unlimited | effectively unlimited | ❌ **not installed** |

The user's instinct: *"if Claude is the lead, that's a problem"* — fearing the limited Claude
quota becomes the bottleneck for an always-on lead, and wanting the unlimited Gemini to carry load.

A 4-expert panel + a focused 2-expert topology review **unanimously inverted that instinct**, and a
read-only code/playbook audit (the "B" verification) **confirmed the load-bearing premise**. This
doc records the validated conclusion and the minimal seam to implement it.

## The load-bearing premise — VERIFIED

> **In this architecture, "lead" == "the MCP client". The lead is the *lowest* token consumer; the
> teammates (coding loops) are the heavy consumers.**

Token profile (per the panel, grounded in this repo's design):

| Role | What it does | Tokens (rough) |
|------|--------------|----------------|
| **lead** (1) | bootstrap read of TEAM.md + playbook, then short MCP tool calls (spawn/mail/task), then synthesize mailed findings into a user summary. Does **not** read/edit files or run tests. | ~2k–15k tok/hr |
| **teammate** (3–5 concurrent) | read/edit many files, run tests, ingest large logs, iterate | ~50k–200k+ tok/hr **each** |

Aggregate teammate burn is ~30–100x the lead. So the $20 Claude cap is blown by **coding volume**,
not **coordination volume**. Putting limited-but-premium Claude on the lead is *optimal*, not a problem.

**Audit evidence (`src/agent_team/bundled/`):** every heavy verb is assigned to a teammate, never
the lead:
- `playbooks/new-feature.yaml` — planner "Do not write production code"; implementer "Implement…Run pytest"; tester "Run test commands"; reviewer "Review diff".
- `playbooks/pr-review.yaml` — reviewers "Read-only. Mail findings to lead"; lead only "Output review summary".
- `lead_instructions` in both playbooks are pure orchestration verbs (spawn / approve / shutdown / summarize).
- `ProjectLoader.build_lead_context` (`project_loader.py:78`) feeds the lead only TEAM.md + config + playbook YAML.

**Gap found during the audit:** there is **no enforced guardrail** keeping the lead orchestration-only.
The lead is `claude` with full built-in Read/Edit/Bash tools, and `--strict-mcp-config` restricts only
MCP servers, not those tools. The low-token property currently holds only because the bundled playbooks
happen to delegate everything. A custom TEAM.md/playbook saying "review the code yourself" would silently
turn the lead into a high-token consumer. → **D6 below closes this gap.**

## Empirical validation + token-efficiency gaps (S10 E2E, 2026-06-15)

The S10 manual E2E — a Claude/Opus lead orchestrating planner(claude) →
implementer(codex) → tester(codex) → reviewer(claude) to build a refund feature
— is the first real-token data point. It **confirms the premise** (coordination
≪ coding) but a 3-expert review of the lead's *observed* behavior found the lead
ran ~2× more expensive than necessary, all from **avoidable** patterns the
bundled playbooks don't yet prevent:

| Waste pattern | What happened in the E2E | Closed by |
|---------------|--------------------------|-----------|
| **Polling shell-watchers** | The lead armed background Bash loops (`for i in $(seq 1 150); test -f docs/plans/refunds.md`) to wait out each stage; one timed out at ~7.5 min and triggered extra investigation. The orchestrator ALREADY emits `teammate_ready`/`task_*`/`mail_sent` to `events.jsonl` (watchfiles) — lead-side polling is pure redundancy. | **D8** |
| **Redundant independent verification** | The lead re-ran `pytest`, re-`type`d source files, ran `git status` — redoing work the teammates already reported and the tester already verified. ~25–35% of lead tokens. | **D6** (strengthen) + **D8** |
| **Unbounded reads** | `read_messages` returns the whole lead inbox unfiltered; `reconcile_handled` reads the *entire* `events.jsonl` on attach. A teammate mailing a large diff/log floods the lead. | **D9** |
| **Verbose self-summaries** | Multi-paragraph prose recaps (2–3 min reasoning turns). | **D6** (terse-output line) |

Estimate: **~10–15k tok/feature observed; ~6–8k achievable** after the fixes. On
the $20 Claude cap that is the difference between ~1 and ~2 full features per
usage window. **Verdict:** the $20 lead is viable — but only once D6/D8/D9 make
the low-token property *structural* instead of hoping the lead is disciplined.
Model tier follows the same logic: **Sonnet lead is fine for scoped features
(routing/triage), reserve Opus for ambiguous-goal decomposition, blocker
re-planning, and done-ness judgment.**

The same E2E also surfaced two reliability/observability gaps now folded into
S11 hardening: teammate work has no durable transcript (**D10**), and the
teammate kickoff `send_keys` fires before the CLI is input-ready (**D11**).

## Core decision — role allocation

| Role | Assignment | Why |
|------|------------|-----|
| **lead** | **Claude** (sole MCP client) | only fully-verified MCP lead; low-token so the $20 cap rarely binds; highest leverage (a bad orchestration decision wastes downstream tokens). Locked orchestration-only (D6). |
| **implementer / tester** (heavy coding) | **Gemini/Antigravity** (unlimited) | highest-volume role → the unlimited tier absorbs it. Failure is locally contained (lead respawns). |
| **reviewer / hard problems** | **Codex** selectively | reserve the $440 plan as a *call-in specialist*, never a standing concurrent teammate. |
| **planner** ("brain" work the user wanted on Gemini) | **Gemini teammate** | see topology note — a Gemini planner persona, not a second lead. |

**Interim (today, only claude+codex verified):** lead = Claude, teammates = Codex/Claude, until
Gemini clears the verification gates. Then Gemini drops into the teammate roles.

## Topology decision — flat (reject the extra "팀장" layer)

The user asked whether *"Claude always calls Gemini as 팀장, distributes codex/gemini teammates"* is
structurally easier. Evaluated three readings:

| Option | Meaning | Verdict |
|--------|---------|---------|
| **B3 — flat (CHOSEN)** | Claude = sole MCP lead; Gemini/codex = flat teammates; a Gemini *planner teammate* does the heavy "thinking" | **easiest, lowest-risk, already on the roadmap** |
| B1 — brain/hands relay | Gemini decides → Claude executes via MCP | ❌ optimizes the cheap (low-token) layer; adds an off-ledger relay + split-brain over task state |
| B2 — nested sub-lead | Claude top-lead spawns Gemini sub-lead with its own MCP + sub-team | ❌ strict superset of "Gemini as direct MCP lead" + recursion + session isolation; depends on the single most-likely-to-fail capability |

**The real structural win:** keep Claude as the *sole* MCP client → **Gemini's MCP support never has
to be verified at all.** The one fragile per-CLI capability (MCP client on Windows headless) is confined
to the one CLI that has it verified. Teammates need no MCP — just "installs + runs headless in a pane +
uses the `agent-team` shell helper."

**The conflation to avoid:** *"Gemini does the heavy thinking"* (high-token → worker role, valuable) vs
*"Gemini is the lead"* (structural MCP role, low-token, unverified on Gemini). Different axes; only the
first saves money. The user's "Gemini planner" desire is satisfied safely by spawning a **Gemini planner
teammate** on the existing mail bus: Claude mails it the goal → Gemini plans in the open → replies via
`agent-team mail` → Claude executes via MCP. Same token routing, fully logged in `event_log`, no second
MCP client, no split-brain.

## Lead/teammate CLI decoupling (load-bearing invariant)

The whole plan assumes free mix-and-match — *any* verified lead CLI can build a team of *any* verified
teammate CLIs (Claude lead + Gemini teammates, Codex lead + Gemini/Codex teammates, etc.). That freedom
exists because of one invariant that must NOT be broken:

> **The lead does not spawn teammates itself. It only *requests* a spawn via the `spawn_teammate` MCP
> tool; the CLI-agnostic agent-team MCP server (Python + psmux) performs the actual launch. The teammate's
> CLI is decided by the persona, never by the lead.**

Code evidence (today):
- The lead's call is `spawn_teammate(persona, prompt, name)` — `mcp_server.py:279`. **No CLI argument** —
  the lead chooses a *role*, not a binary.
- The teammate CLI is resolved from the persona, not the lead: `cli=persona_obj.cli` at
  `mcp_server.py:164-168` (`requested_by="lead"`).
- Actual launch is `psmux.split_pane(command=persona.cli, …)` in `TeammateRunner.spawn` — plain Python,
  independent of which CLI is in the lead pane.

Consequence: the only CLI-specific surface is **lead launch** (D1–D3). The spawn path is already
CLI-agnostic. **Do not** "optimize" by having the lead exec teammates directly — that would couple
teammate choice to the lead CLI and destroy the mix-and-match property this plan depends on.

Requirements for a heterogeneous team under a non-Claude lead: (1) the lead CLI can *call* the
`spawn_teammate` MCP tool — verified for Codex (handshake returned all 9 tools); (2) each teammate CLI is
registered `supports_teammate=True` and installed; (3) the persona YAML's `cli:` names it. The lead CLI's
identity is irrelevant to all three.

## Design decisions (the S11 seam)

| # | Item | Decision |
|---|------|----------|
| D1 | Lead launch dispatch | Generalize `orchestrator._build_lead_launch_command` from the `if cli == "claude"` special-case into a per-CLI dispatch keyed on `CliSpec`. Stays an `elif` chain (no Protocol/ABC), consistent with the S9 decision. Add the `codex` branch. |
| D2 | MCP config renderer | Split the single hardcoded JSON renderer (`_write_lead_mcp_config`, JSON `claude-mcp.json`) into a format-dispatched renderer. Add a `mcp_format` field to `CliSpec` (`"json"` for claude, `"toml"` for codex). `mcp_config_filename` already exists on `CliSpec`. |
| D3 | Codex as 2nd verified lead | `cli_registry`: set `codex` `supports_lead=True`, `mcp_config_filename="codex-mcp.toml"` (or inline `-c`), `mcp_format="toml"`. Launch via `codex exec` + `--ignore-user-config` (global-MCP isolation, the `--strict-mcp-config` equivalent) + the agent-team server injected. System prompt via the PROMPT arg + the lead's AGENTS.md (codex has no `--append-system-prompt-file`). |
| D4 | Config-driven role assignment | Lead via `config.yaml: lead_cli`; teammate-to-CLI via per-persona YAML `cli:` field. Code only knows *capabilities* (registry flags); config decides *assignment*. Switching lead = one-line `lead_cli` flip → cheap A/B / reversibility. |
| D5 | Gemini/Antigravity | **Stay UNREGISTERED** in `cli_registry` until all verification gates pass (a registry entry without a launch builder is a dead spawn path). Use as a *teammate* first (low bar, captures most savings); promote to lead only if/when gates pass — then it is a config + renderer drop-in, no rebuild. |
| D6 | Lead orchestration-only preamble | Add a base lead system-prompt preamble (currently absent — `build_lead_context` has no role framing) that says: *orchestrate only; delegate all file reads/edits/tests to teammates; never review or write code directly; keep context lean*. This locks the low-token property **structurally**, not by playbook convention. |
| D7 | No nested leads | Single-lead + flat-teammate model is retained. B1/B2 explicitly rejected. |
| D8 | Event-driven lead wait (no polling) | The lead must NOT poll with shell loops. Add a `wait_for_event(types, since, timeout)` / `get_recent_events(since, limit)` MCP tool backed by `events.jsonl` (the orchestrator already writes `teammate_ready`/`task_completed`/`mail_sent` there via watchfiles). The lead calls it once when expecting a stage to finish instead of arming a Bash watcher. D6 preamble gains a line forbidding shell-loop polling. **Single biggest lead-token saver (5–10k/session).** |
| D9 | Bounded + filtered reads | `read_messages` gains `from_`/`since` filtering (today it returns the full inbox); `EventLog.read` + `reconcile_handled` gain a tail `limit` so a long-running session doesn't re-ingest the whole log. Caps the lead's worst-case context bloat. |
| D10 | Teammate transcript capture | At spawn, pipe each teammate pane to `{session_dir}/teammates/{name}/transcript.log` via psmux `pipe-pane`. The `events.jsonl` coordination trail + mail summaries do NOT capture a teammate's reasoning/edits; this gives a durable per-teammate work record. `agent-team logs export` bundles transcripts + events. The transcript lives on disk and is **never pulled into the lead's context** (D6), so observability does not cost lead tokens. |
| D11 | Teammate kickoff input-readiness | The kickoff `send_keys` fires immediately after `split_pane`, before the teammate CLI is ready for input — codex's first-run "trust this folder?" prompt eats the keystrokes, so the kickoff (and its Enter) drop and the teammate sits idle. CLI-neutral fix (retry until the ready-marker appears, or await an input-ready signal). **Prerequisite for parallel/gemini teammates** (same failure would hit them). Tracked as its own task; referenced here because it gates smooth multi-CLI teammate spawning. |

## Lead orchestration-only preamble (D6) — exact text

Prepended to the lead system prompt (ahead of TEAM.md + config + playbook) by `build_lead_context`.
CLI-agnostic — applies whether the lead is Claude, Codex, or a future gated CLI.

```text
You are the team LEAD. Your only job is orchestration — not coding.

- Coordinate the team EXCLUSIVELY through the agent-team MCP tools:
  spawn_teammate, send_message, create_task, claim_task, complete_task, list_teammates.
- NEVER read, edit, write, or review project code yourself. Delegate every file read,
  edit, test run, and code review to a teammate — that is what teammates are for.
- Your only outputs are: spawn/approval decisions, task assignments, mail to teammates,
  and a final synthesis built from teammates' MAILED findings (never from raw files/diffs).
- Keep your context lean. Do not pull large files, diffs, or logs into your own context.
  If code must be understood, spawn a teammate to read it and mail you a short summary.
- Treat the playbook as a guide, and honor the config allowlists (max_teammates,
  allowed_personas). Spawn only with user approval; shut teammates down when their stage ends.
```

Rationale: the lead runs on a quota-limited CLI by design (it is the *lowest*-token role). This
preamble keeps it that way structurally, so neither a custom TEAM.md/playbook nor model drift can
turn the lead into a high-token consumer. A unit test asserts the preamble is present in the
rendered lead context (see Test slots / Verification).

## Lead launch — codex branch (sketch)

Claude (today, unchanged):
```
claude --mcp-config {session_dir}\claude-mcp.json --strict-mcp-config \
       --append-system-prompt-file {session_dir}\lead-system-prompt.md
```

Codex (S11, verified flags):
```
codex exec --ignore-user-config \
  -c 'mcp_servers.agent-team.command="python"' \
  -c 'mcp_servers.agent-team.args=["-m","agent_team.mcp_server"]' \
  -c 'mcp_servers.agent-team.env.AGENT_TEAM_SESSION_ID="<sid>"' \
  -c 'mcp_servers.agent-team.env.AGENT_TEAM_PROJECT_PATH="<path>"' \
  --output-last-message {session_dir}\lead-last.txt \
  "<lead system prompt + bootstrap instruction>"
```
`--ignore-user-config` blocks the user's global `~/.codex/config.toml` MCP servers (isolation parity
with `--strict-mcp-config`). The agent-team server is injected via repeated `-c` (or a rendered
`codex-mcp.toml` profile via `--profile`). System prompt rides the PROMPT arg + the lead dir's AGENTS.md.

## Verification gates for Gemini/Antigravity (must ALL pass on THIS Windows machine)

Reproduce on the box, not inferred from docs — the same bar `codex` already cleared.

| Gate | Requirement |
|------|-------------|
| G0 | binary installed, `--version` works, launches from a non-interactive pane (no TTY assumption) |
| G1 | headless single-shot (`-p`/`exec`) returns output and **exits cleanly** (no REPL/hang/keypress) |
| G2 | registers the agent-team MCP server, completes a handshake returning **all 9 tools**, and **calls** at least one tool round-trip |
| G3 | global-MCP isolation flag exists and works (only our server loaded; global config NOT inherited) |
| G4 | system-prompt / AGENTS.md injection actually applies (probe with a required output token) |
| G5 | survives a long-running pane (hours / many turns): no auth expiry, no wedge; degrades gracefully on quota limits |
| G6 | predictable failure semantics (kill/timeout/restart; orchestrator detects a dead lead; no zombie pane) |

Soft G7: primary-source confirmation that Windows + headless + MCP is a *supported* config (today only
secondary sources attest the Antigravity `agy` CLI; its Managed Agent API has **no MCP** — wrong surface).
Run this as a parallel spike, **off the S10/S11 critical path**.

## Cost traps / risks (panel-flagged)

- **Worst value:** Codex ($440) as a default *concurrent coding teammate*. Expensive model × heaviest role × concurrency. Keep Codex as a call-in specialist only.
- **Lead scope-creep (OBSERVED in S10, not hypothetical):** the lead re-ran tests, re-read files, and armed polling shell-watchers — ~2× the necessary token burn. Silently migrates the lead into the expensive column. → D6 (preamble) + D8 (event-driven, no polling) + D9 (bounded reads) mitigate. This is the single most important cost fix for the $20-lead premise.
- **Reliability SPOF:** betting the lead (non-hot-swappable, derails the whole team on failure) on the *unverified* Gemini MCP path. → D5 keeps Gemini out of the lead seat until gated.
- **Teammate helper on Gemini:** before committing Gemini to teammates, confirm the `agent-team` shell helper runs headless under Gemini/Antigravity on Windows (cheap test; avoids noisy respawn loops).

## Phasing

- **DONE (S10):** payment-api E2E passed with **Claude lead + Codex/Claude teammates**. The CLI-neutral seam landed across S9/S10a (lead launch via `shutil.which` + CLI-agnostic `split_pane(command=persona.cli)`). D1/D2 (full per-CLI dispatch + format-dispatched renderer) are not yet done — codex-as-lead still needs them.
- **S11a — $20-lead hardening (do first; highest ROI, no new CLI):** **D6** (orchestration-only preamble) + **D8** (event-driven wait, kill polling) + **D9** (bounded/filtered reads). These make the cost-aware premise real and are the direct payoff of the S10 token review. Pure Claude-lead; no multi-CLI risk.
- **S11b — observability/reliability hardening:** **D10** (teammate transcript capture) + **D11** (kickoff input-readiness — also a standalone task). D11 gates smooth parallel/gemini teammates.
- **S11c — Codex as 2nd lead:** **D1** + **D2** + **D3** + **D4** (config-driven assignment). Proves the seam is real and gives the cost dial (flip `lead_cli`, no code change to revert).
- **DEFER (parallel spike):** Gemini/Antigravity — **D5**. Teammate-first once G0/G1 pass; lead only after G0–G6.

## Touch points

| File | Change |
|------|--------|
| `src/agent_team/cli_registry.py` | add `mcp_format` to `CliSpec`; flip `codex` to `supports_lead=True` + filename/format; keep `antigravity`/`gemini` unregistered |
| `src/agent_team/orchestrator.py` | `_build_lead_launch_command` → per-CLI dispatch (add codex branch); `_write_lead_mcp_config` → format-dispatched (JSON/TOML) renderer |
| `src/agent_team/bundled/templates/lead/` | new: `codex-mcp.toml.j2`; **new base lead preamble** (D6) prepended in `build_lead_context` or written into `lead-system-prompt.md` |
| `src/agent_team/project_loader.py` | `build_lead_context` prepends the orchestration-only preamble (D6) |
| `src/agent_team/bundled/personas/*.yaml` | optional `cli: gemini` once registered; add a Gemini-friendly planner persona |
| `src/agent_team/mcp_server.py` | **D8** new `get_recent_events(since, limit)` / `wait_for_event(types, since, timeout)` tool; **D9** add `from_`/`since` filtering to `read_messages` |
| `src/agent_team/event_log.py`, `orchestrator.py` | **D9** `EventLog.read(..., limit=N)` tail; `reconcile_handled` uses the tail. **D11** kickoff input-readiness in `TeammateRunner.spawn` |
| `src/agent_team/teammate_runner.py`, `cli/logs.py` | **D10** `pipe-pane` each teammate pane → `transcript.log` at spawn; `logs export` bundles transcripts |
| `tests/unit/test_cli_registry.py`, `test_orchestrator.py`, `test_mcp_server.py` | codex-lead spec invariants; codex launch-line + TOML render slots; **preamble-present slot (D6)**; **get_recent_events / read_messages-filter slots (D8/D9)**; **transcript-written slot (D10)** |

## Verification (how to test the implementation)

1. **Unit:** registry invariants for codex-as-lead; `_build_lead_launch_command(cli="codex")` produces the `codex exec --ignore-user-config …` line; TOML renderer emits a parseable `[mcp_servers.agent-team]`; lead context contains the orchestration-only preamble (D6); `get_recent_events`/`wait_for_event` returns events from `events.jsonl` and `read_messages(from_=…)` filters (D8/D9); `EventLog.read(limit=N)` tails (D9); a spawned teammate's `transcript.log` is created and grows (D10).
1b. **Token-efficiency (S11a) acceptance:** re-run the payment-api E2E with the D6/D8/D9 build and confirm the lead no longer arms shell-watchers or re-verifies code; eyeball that per-feature lead token use drops toward the ~6–8k target.
2. **MCP interop (already proven, keep as a smoke test):** standard MCP client handshake against `python -m agent_team.mcp_server` returns the 9 tools; `codex mcp add` accepts the agent-team server.
3. **Live E2E (S11 acceptance):** `agent-team start` with `lead_cli: codex` on a fixture project → codex pane launches, connects to the agent-team MCP server, and successfully calls `spawn_teammate` round-trip. This is the one live, model-spending check not yet run (kept out of plan-time to avoid cost/side-effects).
4. **Gemini gates:** the G0–G6 checklist above, scripted and reproduced on this Windows box, before any registry entry.

## Carried backlog (real, not yet scheduled into S11a/b/c)

Deferred items from earlier reviews + the S10 token review that are NOT yet
placed in a phase and are NOT rejected — recorded here so they aren't lost.

- **`Orchestrator.shutdown` + session archive** (s9-api-sketch out-of-scope; no
  method exists today). Current teardown is per-teammate `shutdown_teammate`
  (kills pane + drops member) + `orchestrator_stopped` on Ctrl-C. Missing: one
  graceful "end session" path that kills all panes, flushes, and archives the
  session dir (events + D10 transcripts) for later inspection. Natural pairing
  with D10 + `logs export`.
- **Model-tier wiring (cost dial, part 2).** `Persona.model_hint`
  (`personas.py:27`) already EXISTS but is a **dead field** — never applied to
  the teammate launch — and there is no `lead_model` config knob. The S10 token
  review's "Sonnet lead for routine / Opus for hard, cheap teammate tiers"
  recommendation therefore has no implementation path. Wire `model_hint` into
  each CLI's launch (claude `--model`, codex `-m`) + add `lead_model` to config.
  Same shape as D4 (config decides; code knows only capabilities).
- **Strict playbook mode.** Only `playbook_mode: guide` is implemented. The
  token review flagged a `strict` (hard-pipeline) mode that lets a cheaper/Sonnet
  lead just gate approvals instead of improvising. Optional — add only if the
  guide-mode lead is still too token-hungry after D6/D8.

Effectively closed (no longer needed): **codex-specific AGENTS.md sections**
(s9 out-of-scope) — subsumed by the CLI-neutral single-line "read your brief"
kickoff (S10a); the shared brief worked for codex teammates in the S10 E2E.

## Out of scope (later)

- Nested / recursive sub-leads (B2) — rejected.
- Brain/hands relay orchestration (B1) — rejected.
- A generic plugin abstraction for a 3rd MCP config format — build only JSON + TOML until a 3rd is verified.
- Auto-sync of bundled vs repo-root templates (still manual per the IMPLEMENTATION.md policy).
- Gemini/Antigravity lead support — gated behind G0–G6, not part of S11 delivery.
