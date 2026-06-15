# S12a — Gemini as teammate (D5 partial): Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Register `gemini` as a hands-off TEAMMATE CLI (the cost-win: unlimited quota on the heaviest coding role) and add Gemini personas — landing the code now, with the live gemini behavior verified via a `tests/manual/` checklist (G0/G1 + the D12-analog).

**Architecture:** Pure teammate-path change — no new launch builder (the CLI-neutral `split_pane(command=persona.cli) + registry teammate_launch_args` path, proven for codex in S11b, handles gemini). **Registry:** add a `gemini` `CliSpec` (`supports_teammate=True`, `supports_lead=False`, `teammate_launch_args` = gemini's interactive auto-approve flags). **Personas:** add `gemini-implementer` + `gemini-planner` bundled YAMLs with `cli: gemini`. The lead still only names a persona; the runner reads gemini's flags from the registry — decoupling invariant intact. Reference spec: `docs/s11-multi-cli-plan.md` ("S12a — Gemini as teammate", D5, "Lead/teammate CLI decoupling", D12).

**Tech Stack:** Python 3.12, pytest, ruff. psmux mocked. The live gemini behavior (headless/interactive launch, auto-approve, the `agent-team` shell helper running under gemini, transcript) is **not** auto-tested — it needs the real binary + tokens + auth; it is the `tests/manual/` G-gate + S12a checklist (Task 3), per the project's live-test policy.

---

## Design decisions resolved before this plan (user-confirmed + gemini-verified)

1. **Scope split (user-confirmed):** S12a (teammate) lands CODE now; S12b (lead) stays plan-only until G0–G6 pass. This plan is S12a.
2. **gemini teammate runs INTERACTIVELY in its pane** (like the codex teammate), launched bare via `split_pane` and triggered by the send_keys kickoff. So its `teammate_launch_args` are the INTERACTIVE auto-approve flags `--approval-mode yolo --skip-trust` — **NOT** `-p`/`--prompt` (that is headless single-shot, which runs once and exits and would never accept the kickoff). `--approval-mode yolo` auto-approves all tools (the D12-analog); `--skip-trust` skips the workspace-trust prompt (the D11-analog for the trust prompt).
3. **D5 reconciliation:** D5 says "stay unregistered until gates pass" to avoid a *dead spawn path*. For a TEAMMATE there is no launch builder to be missing — the generic path already works (codex proved it). So registering gemini as a teammate is not a dead path; the only unknown is whether gemini actually runs hands-off on this box (G0/G1 + auto-approve), which is the `tests/manual` gate. The bundled gemini personas are opt-in (a project must add them to `allowed_personas`), so landing the code cannot silently break existing claude/codex teams. A registry comment marks gemini teammate as "pending live G0/G1 verification".
4. **`gemini` lead stays UNregistered for lead** (`supports_lead=False`): S12b adds that after G0–G6 (separate plan).
5. **antigravity (`agy`) deferred:** `agy` has no MCP subcommand (no `agy mcp`), so it cannot be a lead and cannot coordinate as a standard teammate via MCP. Recorded as "researched, deferred" — NOT registered in S12a.

## Invariant guard (do NOT break)

Lead names only a persona; the runner resolves `persona.cli` and reads `teammate_launch_args` from the registry. Adding gemini must not introduce any lead-side CLI/flag knowledge. (Same invariant S11b's D12 preserved for codex.)

---

## File Structure

- Modify: `src/agent_team/cli_registry.py` — add the `gemini` `CliSpec` (teammate-only) + a comment. **(S12a registry)**
- Create: `src/agent_team/bundled/personas/gemini-implementer.yaml`, `src/agent_team/bundled/personas/gemini-planner.yaml` (`cli: gemini`). **(S12a personas)**
- Test: `tests/unit/test_cli_registry.py`, `tests/unit/test_personas.py`, `tests/unit/test_teammate_runner.py`.
- New: `tests/manual/s12-gemini-gates.md` (the G0–G6 verification spike), `tests/manual/s12a-gemini-teammate.md` (S12a live checklist). Docs: `PROGRESS.md`.

**Task order:** Task 1 (register gemini) MUST precede Task 2 (gemini personas) — the persona loader rejects any `cli` not in the registry, so a `cli: gemini` persona would fail to load until gemini is registered. Task 3 last.

---

## Task 1: Register gemini as a teammate CLI

**Files:**
- Modify: `src/agent_team/cli_registry.py`
- Test: `tests/unit/test_cli_registry.py`

- [ ] **Step 1: Write the failing tests**

In `tests/unit/test_cli_registry.py`, add:

```python
def test_gemini_registered_teammate_only() -> None:
    spec = get_cli_spec("gemini")
    assert spec.supports_teammate is True
    assert spec.supports_lead is False  # lead is S12b, after G0-G6
    assert spec.mcp_config_filename is None
    assert spec.mcp_format is None  # teammate-only needs no lead MCP format
    assert is_teammate_supported("gemini") is True
    assert is_lead_supported("gemini") is False


def test_gemini_teammate_launch_args_are_interactive_auto_approve() -> None:
    spec = get_cli_spec("gemini")
    # INTERACTIVE auto-approve (the teammate runs in a pane + receives the
    # send_keys kickoff) — NOT -p/--prompt (that is headless single-shot).
    assert spec.teammate_launch_args == ("--approval-mode", "yolo", "--skip-trust")
    assert "-p" not in spec.teammate_launch_args
    assert "--prompt" not in spec.teammate_launch_args
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/unit/test_cli_registry.py -k "gemini_registered or gemini_teammate_launch_args" -v`
Expected: FAIL — `get_cli_spec("gemini")` raises `UnknownCliError` (gemini not registered).

- [ ] **Step 3: Register gemini in `_REGISTRY`**

In `src/agent_team/cli_registry.py`, add the gemini entry to `_REGISTRY` (after the codex entry, before the antigravity/gemini comment):

```python
    "gemini": CliSpec(
        name="gemini",
        supports_lead=False,  # S12b promotes to lead after G0-G6 pass
        supports_teammate=True,
        mcp_config_filename=None,
        # D12-analog: gemini teammate runs INTERACTIVELY in its pane and gets the
        # send_keys kickoff, so these are the interactive auto-approve flags (NOT
        # -p, which is headless single-shot). yolo auto-approves all tools;
        # skip-trust skips the workspace-trust prompt. Pending live G0/G1
        # verification on this box — see tests/manual/s12-gemini-gates.md.
        teammate_launch_args=("--approval-mode", "yolo", "--skip-trust"),
        mcp_format=None,
    ),
```

Update the trailing comment in `_REGISTRY` to: `# antigravity (agy): no MCP subcommand — not viable as lead/MCP-teammate; deferred.`

- [ ] **Step 4: Run the targeted + full registry tests**

Run: `python -m pytest tests/unit/test_cli_registry.py -v`
Expected: PASS — new gemini tests green; `test_spec_invariant` (parametrized over `_REGISTRY`, now incl. gemini) passes because gemini is teammate-only with `mcp_format=None`/`mcp_config_filename=None` (the invariant only constrains leads); `test_antigravity_is_not_registered` still passes (antigravity stays unregistered).

- [ ] **Step 5: Commit**

```bash
git add src/agent_team/cli_registry.py tests/unit/test_cli_registry.py
git commit -m "feat(s12a): register gemini as a teammate CLI

gemini CliSpec: supports_teammate=True (lead deferred to S12b), teammate_launch_args
= interactive auto-approve flags (--approval-mode yolo --skip-trust; NOT -p, which
is headless single-shot). Read by the runner from the registry — decoupling intact.
Live G0/G1 verification pending (tests/manual/s12-gemini-gates.md).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Add Gemini personas (implementer + planner)

**Files:**
- Create: `src/agent_team/bundled/personas/gemini-implementer.yaml`, `gemini-planner.yaml`
- Test: `tests/unit/test_personas.py`, `tests/unit/test_teammate_runner.py`

**Depends on Task 1** (persona loader rejects unregistered `cli`).

- [ ] **Step 1: Write the failing tests**

In `tests/unit/test_personas.py`, add:

```python
def test_gemini_personas_bundled(persona_registry: PersonaRegistry) -> None:
    personas = persona_registry.load_all()
    assert personas["gemini-implementer"].cli == "gemini"
    assert personas["gemini-planner"].cli == "gemini"
```

In `tests/unit/test_teammate_runner.py`, add (matches the existing `_spawn_kwargs` helper + `runner` fixture):

```python
def test_spawn_gemini_applies_interactive_auto_approve_args(
    runner: TeammateRunner,
    psmux_backend: PsmuxBackend,
    tmp_path: Path,
) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    runner.spawn(
        **_spawn_kwargs(
            session_dir=session_dir,
            project_path=project,
            teammate_name="helper-gem",
            persona="gemini-implementer",
        )
    )
    split = next(c for c in psmux_backend.recorded_calls if "split-window" in c.args)
    joined = " ".join(split.args)
    assert "gemini" in joined
    assert "--approval-mode" in joined
    assert "yolo" in joined
    assert "--skip-trust" in joined
    # Interactive, not headless: neither -p nor --prompt in the launch command
    # (both are gemini's headless single-shot mode, which would exit before the
    # kickoff). Two checks: ` -p ` catches the short flag; `--prompt` the long one.
    assert " -p " not in f" {joined} "
    assert "--prompt" not in joined
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/unit/test_personas.py::test_gemini_personas_bundled tests/unit/test_teammate_runner.py::test_spawn_gemini_applies_interactive_auto_approve_args -v`
Expected: FAIL — the gemini personas do not exist (`PersonaNotFoundError`/KeyError).

- [ ] **Step 3: Create `gemini-implementer.yaml`**

Create `src/agent_team/bundled/personas/gemini-implementer.yaml` (mirror the `implementer.yaml` shape):

```yaml
name: gemini-implementer
description: Implementation and code changes (Gemini, unlimited quota)
cli: gemini
model_hint: default
tools_hint: workspace-write

spawn_prompt_template: |
  You are the Implementer teammate (Gemini).
  Claim tasks from the task board before starting.
  Follow TEAM.md conventions and existing code style.
  Run tests after each meaningful change.
  Use `agent-team mail send` to report blockers or completion.

coordination_cli:
  - agent-team mail send --to {to} --body "..."
  - agent-team mail read --session {session_id}
  - agent-team task list
  - agent-team task claim --id {task_id}
```

- [ ] **Step 4: Create `gemini-planner.yaml`**

Create `src/agent_team/bundled/personas/gemini-planner.yaml`:

```yaml
name: gemini-planner
description: Planning and decomposition (Gemini, unlimited quota)
cli: gemini
model_hint: default
tools_hint: read-only

spawn_prompt_template: |
  You are the Planner teammate (Gemini).
  Do not write production code — produce a plan/decomposition.
  Read the relevant files, then write the plan where the task says.
  Use `agent-team mail send` to deliver the plan to the lead.

coordination_cli:
  - agent-team mail send --to {to} --body "..."
  - agent-team mail read --session {session_id}
  - agent-team task list
  - agent-team task claim --id {task_id}
```

- [ ] **Step 5: Update the existing tests that pin the bundled persona set**

Adding two bundled personas breaks tests that assert the exact bundled set. Confirmed breakers + fixes:

1. `tests/unit/test_personas.py::test_bundled_personas_load` — it asserts the EXACT set
   `{"planner", "implementer", "reviewer", "tester"}`. Extend it (do NOT weaken):
   ```python
   assert set(personas) == {
       "planner", "implementer", "reviewer", "tester",
       "gemini-implementer", "gemini-planner",
   }
   ```

2. `tests/unit/test_teammate_runner.py::test_spawn_passes_persona_cli_to_split_pane` — add a
   gemini case to its `@pytest.mark.parametrize` (regression hook that the gemini CLI name
   reaches psmux):
   ```python
   @pytest.mark.parametrize(
       "persona,expected_cli",
       [("planner", "claude"), ("implementer", "codex"), ("gemini-implementer", "gemini")],
   )
   ```

3. SAFE (do NOT change): `tests/unit/test_mcp_server.py::test_list_personas_filters_allowed`
   asserts the set returned by `list_personas`, but it is FILTERED by the fixture's
   `allowed_personas` (which has no gemini), so it stays green. Confirm by running it.

Then run the persona/mcp/runner suites; if any OTHER test pins the bundled set/count, extend
it to include the two gemini personas (never delete/weaken an assertion).

- [ ] **Step 6: Run the targeted + persona/runner suites**

Run: `python -m pytest tests/unit/test_personas.py tests/unit/test_teammate_runner.py -v`
Expected: PASS — gemini personas load (cli validated against the now-registered gemini); the spawn test shows the interactive auto-approve args in the split-window command; existing tests green (claude/codex spawn tests unaffected — gemini args only apply to gemini personas).

- [ ] **Step 7: Commit**

```bash
git add src/agent_team/bundled/personas/gemini-implementer.yaml src/agent_team/bundled/personas/gemini-planner.yaml tests/unit/test_personas.py tests/unit/test_teammate_runner.py
git commit -m "feat(s12a): add gemini-implementer + gemini-planner personas

cli: gemini personas (heavy coding + planning, unlimited quota). Spawned via the
generic teammate path; the runner applies the registry's interactive auto-approve
launch args. Opt-in (a project must add them to allowed_personas).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: G-gate spike + S12a live checklist + PROGRESS

**Files:**
- New: `tests/manual/s12-gemini-gates.md`, `tests/manual/s12a-gemini-teammate.md`
- Modify: `PROGRESS.md`

- [ ] **Step 1: Write the G0–G6 verification spike checklist**

Create `tests/manual/s12-gemini-gates.md` (style of `tests/manual/s11c-codex-lead.md`). It is the on-machine, reproduce-not-infer gate the user runs. Tag each gate free/token, auth, teammate-vs-lead. Content:

```markdown
# S12 gemini verification gates (G0–G6) — run on THIS Windows box

Reproduce live, not inferred from docs. G0/G1 + auto-approve gate S12a (teammate);
G2–G6 gate S12b (lead). gemini 0.46.0.

## Free checks (no tokens)
- [ ] G0: `gemini --version` → prints version, exit 0. Launches from a non-TTY
      psmux pane (no TTY assumption).
- [ ] `gemini --help | Select-String "prompt"` shows `-p/--prompt` (headless).
- [ ] `gemini --help | Select-String "approval-mode"` shows yolo/auto_edit (D12-analog).
- [ ] `gemini mcp list` runs (MCP subcommand exists — lead-relevant).
- [ ] `gemini --help | Select-String "allowed-mcp-server-names"` (isolation flag, lead).

## Token / auth checks
- [ ] G1 (teammate): `gemini -p "say hi"` → returns output AND exits cleanly
      (no REPL/hang/keypress). [token]
- [ ] D12-analog (teammate): an INTERACTIVE `gemini --approval-mode yolo --skip-trust`
      pane accepts a kickoff via psmux send_keys and runs tool calls WITHOUT
      per-command approval or a trust prompt. [token]
- [ ] Helper-under-gemini (teammate): confirm `agent-team` shell helper (mail/task/
      `teammate ready`) runs under gemini on Windows (the teammate brief tells it to).
- [ ] G2 (lead): register `gemini mcp add agent-team python -m agent_team.mcp_server
      -e AGENT_TEAM_SESSION_ID=... -e AGENT_TEAM_PROJECT_PATH=...`; launch with
      `--allowed-mcp-server-names agent-team`; confirm handshake returns all 11 tools
      and one tool round-trips. [token]
- [ ] G3 (lead): with `--allowed-mcp-server-names agent-team`, only our server loads
      (no user global MCP bleed-through). [token]
- [ ] G4 (lead): a `GEMINI.md` in the working root is actually applied (probe with a
      required output token). [token]
- [ ] G5 (lead): survives a long pane (many turns, no auth expiry/wedge; degrades on
      quota). [token]
- [ ] G6 (lead): kill/timeout/restart — orchestrator detects a dead pane, no zombie. [mixed]

## Soft G7
- [ ] Primary-source confirmation that Windows + headless + (CLI) MCP is supported.

## Outcome
- G0/G1 + D12-analog PASS → S12a (gemini teammate) is trustworthy to use.
- ALL G0–G6 PASS → unblocks S12b (gemini lead) implementation.
```

- [ ] **Step 2: Write the S12a live checklist**

Create `tests/manual/s12a-gemini-teammate.md`:

```markdown
# S12a manual checklist — gemini as teammate

Prereq: G0/G1 + D12-analog in s12-gemini-gates.md PASS.

- [ ] In a fixture project's `.agent-team/config.yaml`, add `gemini-implementer`
      (and/or `gemini-planner`) to `allowed_personas`.
- [ ] Start a session (claude lead). Approve a `spawn_teammate(persona=
      "gemini-implementer", ...)`.
- [ ] Confirm: a gemini pane launches with `--approval-mode yolo --skip-trust`
      (interactive), reads its brief (AGENTS.md), runs `agent-team teammate ready`,
      and mails the lead — all WITHOUT manual approval/trust prompts.
- [ ] Confirm D10 transcript `{session_dir}/teammates/<name>/transcript.log` grows.
- [ ] Confirm the lead never named the gemini CLI/flags (decoupling invariant).
- [ ] Cost: confirm the heavy coding role ran on gemini (unlimited quota), not
      claude/codex.
```

- [ ] **Step 3: Add the S12a entry to PROGRESS.md**

In `PROGRESS.md`, add an S12a "done (code)" entry: gemini registered as a teammate CLI (interactive auto-approve launch args), gemini-implementer/planner personas added; live G0/G1 + teammate behavior verified via the new manual checklists; S12b (lead) is plan-only pending G0–G6. Note agy deferred (no MCP). Match the existing style.

- [ ] **Step 4: Full verification**

Run: `python -m pytest tests/ -q`
Expected: PASS — S11's 242 + S12a additions (registry ×2, persona ×1, spawn ×1, + any updated bundled-set assertions).

Run: `python -m ruff check src/ tests/`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add tests/manual/s12-gemini-gates.md tests/manual/s12a-gemini-teammate.md PROGRESS.md
git commit -m "docs(s12a): gemini G0-G6 gate spike + S12a live checklist + PROGRESS

The G0-G6 verification gates (run on the Windows box) and the S12a gemini-teammate
live checklist; PROGRESS S12a entry (code landed; live behavior + S12b lead gated
on the manual gates). agy deferred (no MCP).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage (docs/s11-multi-cli-plan.md "S12a"):**
- Register gemini `supports_teammate=True` (NOT lead) → Task 1. ✓
- `teammate_launch_args` = gemini headless/auto-approve flags (D12 pattern) → Task 1 (corrected to INTERACTIVE auto-approve, not `-p`). ✓
- Add a Gemini persona (planner/implementer) `cli: gemini` → Task 2. ✓
- No new launch builder (CLI-neutral `split_pane` + registry args) → confirmed; nothing added to `_build_lead_launch_command`. ✓
- G0/G1 + D12-analog prerequisite + helper-under-gemini → Task 3 manual gates. ✓
- Decoupling invariant + locally-contained failure → preserved. ✓

**2. Placeholder scan:** No TBD/TODO; complete code/YAML in every code step. Task 2 Step 5 is a "read-then-fix the bundled-set assertions" instruction (a deliberate adapt-to-existing-tests step, not a code placeholder); Task 3 artifacts are manual checklists by design. ✓

**3. Type consistency:**
- gemini `CliSpec(supports_lead=False, supports_teammate=True, mcp_config_filename=None, teammate_launch_args=("--approval-mode","yolo","--skip-trust"), mcp_format=None)` (Task 1) — passes the post-S11c invariant (lead-only constraints don't apply). ✓
- Personas `cli: gemini` (Task 2) validated against the Task-1 registry entry. Task order enforces register-before-persona. ✓
- `teammate_launch_args` consumed by the existing `TeammateRunner.spawn` `" ".join([p.cli, *launch_args])` (S11b) — no runner change needed. ✓

## Expert review axes

- **E1 Registry** — gemini CliSpec correctness, invariant (teammate-only), interactive-vs-headless flag choice, no lead leakage.
- **E2 Personas** — YAML shape/validity, cli validation against registry, bundled-set test updates, allowed_personas/opt-in semantics.
- **E3 Spawn/decoupling** — runner applies gemini args via the generic path; lead names only persona; no `-p` (interactive teammate); transcript/readiness (D10/D11) still apply.
- **E4 Tests** — coverage (registry, persona load, spawn args), no weakened/over-broad assertions, existing claude/codex spawn tests unaffected.
- **E5 Gate/scope** — G0–G6 checklist concreteness; D5 reconciliation (teammate not a dead path; opt-in); agy-deferred recorded; S12b correctly left plan-only.
