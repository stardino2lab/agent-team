# S12a agy (Antigravity) teammate — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the gemini S12a teammate slice with agy (Antigravity) — registry entry, personas, and tests — keeping the suite at 248 passed.

**Architecture:** agy is a Claude-Code-derived agent CLI (`agy.exe`, v1.0.10). It registers as a teammate-only CLI (lead deferred: no MCP subcommand). The teammate runs interactively in its pane and receives the send_keys kickoff; its single auto-approve flag is `--dangerously-skip-permissions` (confirmed in `agy --help`). cli/registry name and binary are all `agy`; persona labels are `agy-implementer` / `agy-planner`. This is a swap of the existing gemini slice — same shape, same test count.

**Tech Stack:** Python, pytest, ruff. Spec: `docs/superpowers/specs/2026-06-19-s12a-agy-teammate-design.md`.

---

### Task 1: Registry — swap gemini CliSpec for agy

**Files:**
- Modify: `src/agent_team/cli_registry.py` (docstring lines 1-10; `_REGISTRY` gemini entry lines 70-82)
- Test: `tests/unit/test_cli_registry.py:145-161`

- [ ] **Step 1: Rewrite the two gemini tests as agy tests**

In `tests/unit/test_cli_registry.py`, replace the block at lines 145-161 with:

```python
def test_agy_registered_teammate_only() -> None:
    spec = get_cli_spec("agy")
    assert spec.supports_teammate is True
    assert spec.supports_lead is False  # lead deferred: no MCP subcommand
    assert spec.mcp_config_filename is None
    assert spec.mcp_format is None  # teammate-only needs no lead MCP format
    assert is_teammate_supported("agy") is True
    assert is_lead_supported("agy") is False


def test_agy_teammate_launch_args_are_interactive_auto_approve() -> None:
    spec = get_cli_spec("agy")
    # INTERACTIVE auto-approve (the teammate runs in a pane + receives the
    # send_keys kickoff) — NOT -p/--print (that is headless single-shot).
    # agy is Claude-Code-derived: one flag covers all tool approvals.
    assert spec.teammate_launch_args == ("--dangerously-skip-permissions",)
    assert "-p" not in spec.teammate_launch_args
    assert "--print" not in spec.teammate_launch_args
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/unit/test_cli_registry.py -q`
Expected: FAIL — `UnknownCliError: Unknown CLI: 'agy'` (agy not yet registered).

- [ ] **Step 3: Replace the gemini registry entry with agy**

In `src/agent_team/cli_registry.py`, replace the `"gemini": CliSpec(...)` block (lines 70-82) and the trailing antigravity comment (line 83) with:

```python
    "agy": CliSpec(
        name="agy",
        supports_lead=False,  # lead deferred: agy has no MCP subcommand
        supports_teammate=True,
        mcp_config_filename=None,
        # agy is Claude-Code-derived: the teammate runs INTERACTIVELY in its pane
        # and gets the send_keys kickoff, so this is the interactive auto-approve
        # flag (NOT -p/--print, which is headless single-shot and would exit before
        # the kickoff). One flag auto-approves all tool permission requests.
        # Confirmed present in `agy --help`. Pending live G1 — see
        # tests/manual/s12-agy-gates.md.
        teammate_launch_args=("--dangerously-skip-permissions",),
        mcp_format=None,
    ),
```

- [ ] **Step 4: Update the module docstring**

In `src/agent_team/cli_registry.py`, replace docstring lines 6-9:

```python
Currently registered: claude (lead + teammate), codex (lead + teammate),
agy (Antigravity, teammate only — lead deferred: agy has no MCP subcommand,
so it cannot yet host the agent-team MCP server). gemini was superseded by agy.
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/unit/test_cli_registry.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/agent_team/cli_registry.py tests/unit/test_cli_registry.py
git commit -m "feat(s12a): register agy as a teammate CLI (replaces gemini)"
```

---

### Task 2: Personas — swap gemini-*.yaml for agy-*.yaml

**Files:**
- Delete: `src/agent_team/bundled/personas/gemini-implementer.yaml`, `gemini-planner.yaml`
- Delete: `personas/gemini-implementer.yaml`, `gemini-planner.yaml`
- Create: `src/agent_team/bundled/personas/agy-implementer.yaml`, `agy-planner.yaml`
- Create: `personas/agy-implementer.yaml`, `agy-planner.yaml` (byte-for-byte mirror)
- Test: `tests/unit/test_personas.py:14-27`, `tests/unit/test_bundled.py:42-49`, `tests/unit/test_teammate_runner.py:154,302-330`

- [ ] **Step 1: Update the persona tests to expect agy**

In `tests/unit/test_personas.py`, replace lines 14-27:

```python
def test_bundled_personas_load(persona_registry: PersonaRegistry) -> None:
    personas = persona_registry.load_all()
    assert set(personas) == {
        "planner", "implementer", "reviewer", "tester",
        "agy-implementer", "agy-planner",
    }
    assert personas["planner"].cli == "claude"
    assert personas["implementer"].cli == "codex"


def test_agy_personas_bundled(persona_registry: PersonaRegistry) -> None:
    personas = persona_registry.load_all()
    assert personas["agy-implementer"].cli == "agy"
    assert personas["agy-planner"].cli == "agy"
```

In `tests/unit/test_bundled.py`, replace the list at lines 42-49:

```python
    assert names == [
        "agy-implementer.yaml",
        "agy-planner.yaml",
        "implementer.yaml",
        "planner.yaml",
        "reviewer.yaml",
        "tester.yaml",
    ]
```

In `tests/unit/test_teammate_runner.py`, change the parametrize at line 154 from
`("gemini-implementer", "gemini")` to `("agy-implementer", "agy")`, and replace the
test at lines 302-330 with:

```python
def test_spawn_agy_applies_interactive_auto_approve_args(
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
            teammate_name="helper-agy",
            persona="agy-implementer",
        )
    )
    split = next(c for c in psmux_backend.recorded_calls if "split-window" in c.args)
    joined = " ".join(split.args)
    assert "agy" in joined
    assert "--dangerously-skip-permissions" in joined
    # Interactive, not headless: neither -p nor --print in the launch command
    # (both are agy's headless single-shot mode, which would exit before the
    # kickoff). ` -p ` catches the short flag; `--print` the long one.
    assert " -p " not in f" {joined} "
    assert "--print" not in joined
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/unit/test_personas.py tests/unit/test_bundled.py tests/unit/test_teammate_runner.py -q`
Expected: FAIL — agy personas not found / gemini files still present.

- [ ] **Step 3: Create the agy persona files (bundled)**

Create `src/agent_team/bundled/personas/agy-implementer.yaml`:

```yaml
name: agy-implementer
description: Implementation and code changes (Antigravity)
cli: agy
model_hint: default
tools_hint: workspace-write

spawn_prompt_template: |
  You are the Implementer teammate (Antigravity).
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

Create `src/agent_team/bundled/personas/agy-planner.yaml`:

```yaml
name: agy-planner
description: Planning and decomposition (Antigravity)
cli: agy
model_hint: default
tools_hint: read-only

spawn_prompt_template: |
  You are the Planner teammate (Antigravity).
  Do not write production code — produce a plan/decomposition.
  Read the relevant files, then write the plan where the task says.
  Use `agent-team mail send` to deliver the plan to the lead.

coordination_cli:
  - agent-team mail send --to {to} --body "..."
  - agent-team mail read --session {session_id}
  - agent-team task list
  - agent-team task claim --id {task_id}
```

- [ ] **Step 4: Mirror to root and delete the gemini files**

Copy both new files byte-for-byte into root `personas/`, then delete all four
gemini files:

```bash
cp src/agent_team/bundled/personas/agy-implementer.yaml personas/agy-implementer.yaml
cp src/agent_team/bundled/personas/agy-planner.yaml personas/agy-planner.yaml
git rm src/agent_team/bundled/personas/gemini-implementer.yaml \
       src/agent_team/bundled/personas/gemini-planner.yaml \
       personas/gemini-implementer.yaml \
       personas/gemini-planner.yaml
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/unit/test_personas.py tests/unit/test_bundled.py tests/unit/test_teammate_runner.py -q`
Expected: PASS. (`test_bundled.py::test_bundled_mirror` byte-equality check confirms the root↔bundled parity.)

- [ ] **Step 6: Commit**

```bash
git add src/agent_team/bundled/personas/ personas/ tests/unit/test_personas.py tests/unit/test_bundled.py tests/unit/test_teammate_runner.py
git commit -m "feat(s12a): add agy-implementer + agy-planner personas (replaces gemini)"
```

---

### Task 3: Full suite + ruff gate

**Files:** none (verification only)

- [ ] **Step 1: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS, **248 passed** (same count as before — gemini cases swapped for agy), no failures.

- [ ] **Step 2: Lint**

Run: `python -m ruff check .`
Expected: clean (no findings).

- [ ] **Step 3: Confirm no stale gemini references remain in code/tests**

Run: `git grep -n gemini -- src tests`
Expected: no output. If any line prints, fix it (it was missed) and re-run Steps 1-3.

---

### Task 4: Manual gate doc — s12-agy-gates.md

**Files:**
- Delete: `tests/manual/s12-gemini-gates.md`
- Delete: `tests/manual/s12a-gemini-teammate.md`
- Create: `tests/manual/s12-agy-gates.md`

- [ ] **Step 1: Write the agy gate doc**

Create `tests/manual/s12-agy-gates.md`:

```markdown
# S12 agy (Antigravity) verification gates — run on THIS Windows box

Reproduce live, not inferred from docs. G0 + G1 + helper gate S12a (teammate).
Lead gates are deferred until the MCP spike (agy has no `mcp` subcommand).
agy 1.0.10.

## Free checks (no tokens) — G0 [DONE 2026-06-19]
- [x] `agy --version` → prints 1.0.10, exit 0. Launches from a non-TTY psmux pane.
- [x] `agy --help` shows `--dangerously-skip-permissions` (auto-approve all tools).
- [x] `agy --help` shows `-p/--print` + `--prompt-interactive` (headless vs interactive).
- [x] `agy help mcp` → "unknown subcommand: mcp" (confirms no MCP subcommand → lead deferred).

## Token / auth checks
- [ ] G1 (teammate): an INTERACTIVE `agy --dangerously-skip-permissions` pane accepts
      a kickoff via psmux send_keys and runs tool calls WITHOUT per-command approval
      or a first-run trust prompt. [token]
- [ ] Helper-under-agy (teammate): confirm the `agent-team` shell helper (mail/task/
      `teammate ready`) runs under agy on Windows (the teammate brief tells it to). [token]

## Deferred (lead — needs an MCP spike)
- [ ] Resolve how agy hosts an MCP server (Claude-Code `.mcp.json` project convention?
      `agy plugin import claude`? a config file under `~/.antigravity/`?). Only then can
      agy be evaluated as a lead. Out of scope for S12a.

## Outcome
- G0 (done) + G1 + helper PASS → S12a (agy teammate) is trustworthy to use.
- Lead is blocked on the MCP spike above.
```

- [ ] **Step 2: Delete the superseded gemini manual docs**

```bash
git rm tests/manual/s12-gemini-gates.md tests/manual/s12a-gemini-teammate.md
```

- [ ] **Step 3: Commit**

```bash
git add tests/manual/s12-agy-gates.md
git commit -m "docs(s12a): agy live gates (G0 done) + drop gemini gate docs"
```

---

### Task 5: Progress / implementation docs

**Files:**
- Modify: `PROGRESS.md` (S12a section + Milestone gates S12 row)
- Modify: `PROGRESS.ko.md` (matching section)
- Modify: `docs/IMPLEMENTATION.md` (any gemini mention in the CLI/registry notes)

- [ ] **Step 1: Find every doc reference to gemini**

Run: `git grep -n gemini -- PROGRESS.md PROGRESS.ko.md docs/IMPLEMENTATION.md`
Note each line.

- [ ] **Step 2: Rewrite the S12a PROGRESS entry**

In `PROGRESS.md`, replace the "S12a implementation (gemini as teammate ...)" section
heading and body to describe agy: registry `agy` (teammate-only, lead deferred — no
MCP subcommand), `teammate_launch_args=("--dangerously-skip-permissions",)`,
`agy-implementer`/`agy-planner` personas, gemini slice superseded. Keep the "248
passed" line (count unchanged). Update the Milestone gates table S12 row to name agy
instead of gemini, and reference `tests/manual/s12-agy-gates.md`. Mirror the same
edits into `PROGRESS.ko.md`.

- [ ] **Step 3: Update IMPLEMENTATION.md**

For each gemini line found in Step 1 under `docs/IMPLEMENTATION.md`, retarget it to
agy (or remove if it was a gemini-specific note that no longer applies). If Step 1
found no IMPLEMENTATION.md hits, skip this step.

- [ ] **Step 4: Verify no stale gemini doc references**

Run: `git grep -n gemini -- PROGRESS.md PROGRESS.ko.md docs/IMPLEMENTATION.md`
Expected: no output (historical mentions inside dated past-milestone entries may
remain if they describe what happened then — but the S12/S12a current-state lines
must all read agy).

- [ ] **Step 5: Commit**

```bash
git add PROGRESS.md PROGRESS.ko.md docs/IMPLEMENTATION.md
git commit -m "docs(s12a): retarget S12 milestone gemini -> agy"
```

---

## Notes for the implementer

- This is a swap, not an addition: the suite count stays 248. If you see 249/250,
  you added an agy case without removing the gemini one — find and remove the leftover.
- The byte-for-byte root↔bundled persona mirror is an enforced invariant
  (`test_bundled.py`). Always edit bundled first, then copy to root.
- Live agy behavior (interactive launch, the trust prompt, the shell helper) is NOT
  unit-tested — it is the `tests/manual/s12-agy-gates.md` G1/helper checks, run later
  with tokens. Do not try to automate them here.
- Do not touch the codex/claude registry entries or the lead path.
