# S10a — CLI-neutral teammate work foundation: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a spawned teammate run in the consumer project's root (so it can edit files / run pytest / git) and receive its context via a single-line "read your brief" kickoff, without per-CLI launch branching.

**Architecture:** Change only `TeammateRunner.spawn`. Keep the launch as bare `split_pane(command=persona.cli, …)` (CLI-neutral invariant). Two behavioral changes: pane cwd becomes `project_path` (was the scratch teammate dir), and the trigger becomes a single-line kickoff that points the teammate at its on-disk brief (the brief itself is unchanged and stays in the scratch dir). Reference spec: `docs/superpowers/specs/2026-06-14-s10a-teammate-work-foundation-design.md`.

**Tech Stack:** Python 3.12, pytest, ruff. psmux backend mocked in unit tests (records argv only).

---

## File Structure

- Modify: `src/agent_team/teammate_runner.py` — add `_kickoff_line` helper; in `spawn`, set non-mock pane cwd to `project_path` and send the single-line kickoff instead of the multi-line `full_prompt`.
- Modify: `tests/unit/test_teammate_runner.py` — update the two assertions that encode the old behavior (scratch cwd, persona-text-in-keys) and add cwd/kickoff/no-flags guards.
- Unchanged: `src/agent_team/bundled/templates/teammate/AGENTS.md.j2` (its "project directory" / "TEAM.md in project root" wording is now correct because cwd *is* the project root). The brief is still written to `{session_dir}/teammates/{name}/AGENTS.md`.

---

## Task 1: Project cwd + single-line kickoff

**Files:**
- Modify: `src/agent_team/teammate_runner.py`
- Test: `tests/unit/test_teammate_runner.py`

- [ ] **Step 1: Update the existing behavioral test and add guards (write the failing tests)**

In `tests/unit/test_teammate_runner.py`, replace the body of
`test_spawn_splits_pane_and_sends_persona_prompt` below the `result = runner.spawn(...)`
line (currently lines 63-80) with assertions for the new behavior:

```python
    assert result.pane_id.startswith("%")
    assert result.teammate_name == "helper-1"
    assert result.persona == "planner"
    assert result.cli == "claude"

    calls = psmux_backend.recorded_calls
    split = next(c for c in calls if "split-window" in c.args)
    # Teammate runs from the PROJECT root so it can edit files / run pytest / git.
    assert split.cwd == str(project.resolve())
    # Launch stays bare `persona.cli` — no per-CLI flags (CLI-neutral invariant).
    joined = " ".join(split.args)
    assert "claude" in joined
    assert "--append-system-prompt" not in joined
    assert "--mcp-config" not in joined

    send = next(c for c in calls if "send-keys" in c.args)
    keys_arg = send.args[send.args.index("-l") + 1]
    # Single-line kickoff (multi-line send_keys would submit line-by-line).
    assert "\n" not in keys_arg
    assert "\r" not in keys_arg
    assert "helper-1" in keys_arg
    # Points the teammate at its on-disk brief by absolute path.
    brief = session_dir / "teammates" / "helper-1" / "AGENTS.md"
    assert str(brief) in keys_arg
    # The role/task text lives in the brief file, not in the kickoff line.
    assert "You are the Planner teammate" not in keys_arg

    assert len(runner.recorded_spawns) == 1
    assert runner.recorded_spawns[0].persona == "planner"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/unit/test_teammate_runner.py::test_spawn_splits_pane_and_sends_persona_prompt -v`
Expected: FAIL — current code sets `split.cwd` to the scratch teammate dir and sends the multi-line `full_prompt` (which contains "You are the Planner teammate" and a newline).

- [ ] **Step 3: Add the `_kickoff_line` helper**

In `src/agent_team/teammate_runner.py`, after the `_MOCK_COMMAND` constant
(line 13), add:

```python
def _kickoff_line(teammate_name: str, brief_path: Path) -> str:
    """Single-line trigger that points the teammate at its on-disk brief.

    Must stay one line: psmux send_keys types embedded newlines literally and
    each one acts as Enter in the teammate's interactive CLI, submitting the
    message line-by-line. The rich role/coordination/task context lives in the
    brief file (read from cwd-independent absolute path), keeping the launch
    CLI-neutral — no per-CLI system-prompt flags.
    """
    line = (
        f'You are agent-team teammate "{teammate_name}". '
        f"Read your brief at {brief_path} "
        "(role, coordination CLI, and your task), then begin. "
        "Project conventions are in TEAM.md/AGENTS.md here."
    )
    return line.replace("\n", " ").replace("\r", " ")
```

- [ ] **Step 4: Rewrite `spawn` to use project cwd + kickoff**

In `src/agent_team/teammate_runner.py`, replace the body of `spawn` (currently
lines 68-106, from `p = self.registry.get(persona)` through the `return`) with:

```python
        p = self.registry.get(persona)
        full_prompt = f"{p.spawn_prompt_template}\n\n{prompt}".strip()

        if self._mock:
            pane_id = self.psmux.split_pane(
                psmux_session, command=_MOCK_COMMAND, cwd=None
            )
        else:
            teammate_dir = session_dir / "teammates" / teammate_name
            teammate_dir.mkdir(parents=True, exist_ok=True)
            brief_path = teammate_dir / "AGENTS.md"
            brief_path.write_text(
                render_bundled_template(
                    "teammate/AGENTS.md.j2",
                    teammate_name=teammate_name,
                    persona_name=persona,
                    session_id=session_id,
                    project_path=str(project_path),
                    spawn_prompt=full_prompt,
                ),
                encoding="utf-8",
            )
            # Run the teammate CLI from the project root so relative file edits,
            # pytest, and git target the real checkout. Trigger it with a
            # single-line kickoff pointing at the absolute brief path.
            pane_id = self.psmux.split_pane(
                psmux_session, command=p.cli, cwd=project_path
            )
            self.psmux.send_keys(
                pane_id, _kickoff_line(teammate_name, brief_path), enter=True
            )

        self.recorded_spawns.append(
            RecordedSpawn(
                persona=persona,
                teammate_name=teammate_name,
                prompt=full_prompt,
                pane_id=pane_id,
            )
        )
        return SpawnResult(
            pane_id=pane_id,
            teammate_name=teammate_name,
            persona=persona,
            cli=p.cli,
            started_at=format_ts(utc_now()),
        )
```

- [ ] **Step 5: Run the targeted tests to verify they pass**

Run: `python -m pytest tests/unit/test_teammate_runner.py -v`
Expected: PASS — all teammate-runner tests green (the brief-render and
mock tests are unaffected; the mock test still sees no `teammates/` dir and no
send-keys).

- [ ] **Step 6: Run the full suite and lint**

Run: `python -m pytest tests/ -q`
Expected: PASS (catch any orchestrator-level test that asserted teammate cwd).

Run: `python -m ruff check src/ tests/`
Expected: `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git add src/agent_team/teammate_runner.py tests/unit/test_teammate_runner.py
git commit -m "feat(s10a): teammate runs in project cwd + single-line kickoff

cwd -> project_path so the teammate can edit files / run pytest / git; trigger
via a single-line 'read your brief' kickoff (multi-line send_keys submitted
line-by-line). Launch stays bare command=persona.cli (CLI-neutral invariant);
brief still written to the session scratch dir, no project pollution.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage:**
- #7 (project cwd) → Task 1 Step 4 (`cwd=project_path`) + Step 1 assertion `split.cwd == str(project.resolve())`. ✓
- #5 (single-line kickoff) → Step 3 `_kickoff_line` + Step 1 assertions `"\n" not in keys_arg`. ✓
- CLI-neutral invariant (bare `persona.cli`, no per-CLI flags) → Step 4 keeps `command=p.cli`; Step 1 asserts `--append-system-prompt`/`--mcp-config` absent. ✓
- Brief unchanged in scratch dir → Step 4 still writes `{session_dir}/teammates/{name}/AGENTS.md`; `test_spawn_renders_agents_md_per_teammate` continues to cover it. ✓
- mock mode unchanged → Step 4 mock branch keeps `_MOCK_COMMAND`, no file, no send_keys; `test_spawn_mock_*` still passes. ✓
- Acceptance = unit green → Steps 5-6. ✓

**2. Placeholder scan:** No TBD/TODO; every code step shows complete code. ✓

**3. Type consistency:** `_kickoff_line(teammate_name: str, brief_path: Path) -> str` defined in Step 3 and called in Step 4 with `(teammate_name, brief_path)` where `brief_path = teammate_dir / "AGENTS.md"` (a `Path`). `Path` already imported in `teammate_runner.py`. ✓
