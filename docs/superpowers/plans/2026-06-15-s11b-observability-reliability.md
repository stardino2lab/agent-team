# S11b — observability/reliability (D10 + D11 + D12): Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make heterogeneous teammates run hands-off and observable: durable per-teammate transcripts (D10), a kickoff that survives CLI startup (D11), and codex teammates that don't block on approval prompts (D12) — all via the registry/runner, never the lead.

**Architecture:** All three are CLI-decoupling-invariant changes confined to the Python runner + backend + registry; the lead is untouched. **D12** adds a registry field `CliSpec.teammate_launch_args` (codex = `--dangerously-bypass-approvals-and-sandbox`) that `TeammateRunner` applies to the `split_pane` command — the lead still only names a persona. **D11** adds `PsmuxBackend.capture_pane` + a CLI-neutral `_wait_until_input_ready` (poll the pane until its output settles, timeout-fallback) so the kickoff `send_keys` lands after the CLI is reading stdin. **D10** adds `PsmuxBackend.pipe_pane` to stream each teammate pane to `{session_dir}/teammates/{name}/transcript.log` at spawn, and extends `agent-team logs export` to bundle events + transcripts. Reference spec: `docs/s11-multi-cli-plan.md` (decisions **D10**, **D11**, **D12**; "Lead/teammate CLI decoupling" invariant).

**Tech Stack:** Python 3.12, pytest, ruff. psmux backend mocked (`PsmuxBackend(mock=True)` records argv only). Live behavior (real pipe-pane transcript on Windows, real codex no-approval run, capture-pane readiness with real CLIs) is verified manually — see Task 6's `tests/manual/` checklist, per the project's live-test policy.

---

## Design decisions resolved before this plan (user-confirmed)

1. **D12 codex teammate flags = `--dangerously-bypass-approvals-and-sandbox`** (registry `teammate_launch_args`). This skips per-command approval prompts, the sandbox (codex OS-sandbox is macOS/Linux-oriented and unreliable on this Windows box), and the first-run trust prompt — fully hands-off on a trusted dev machine. (`--skip-git-repo-check` is a `codex exec`/lead flag, NOT available to the interactive `codex` teammate, so it is intentionally omitted.) claude teammates get `()` (no flags — bare launch, unchanged).
2. **D11 kickoff readiness = capture-pane stabilization.** Poll `capture_pane(pane_id)`; once output is non-empty and unchanged across `settle_count` consecutive polls (the CLI banner has settled at its input prompt), send the kickoff. On timeout, send anyway (fallback). Bounded, CLI-neutral, no double-submit — and it does NOT change the async S10b `teammate_ready` handshake.
3. **D10 transcript = psmux `pipe-pane` at spawn.** The transcript lives on disk only and is NEVER pulled into the lead's context (D6), so observability costs zero lead tokens. The exact pipe redirect command (`cat >> "…"`) is verified live on Windows in the manual checklist (the one cross-platform-risky bit).

## Invariant guard (do NOT break)

The lead never names a CLI or a launch flag. `teammate_launch_args` is read by `TeammateRunner` from `cli_registry` keyed on the **persona's** CLI — the lead only calls `spawn_teammate(persona, …)`. Keep `pipe_pane`/`capture_pane`/`launch_args` entirely inside the runner+backend. This preserves the heterogeneous mix-and-match property the whole multi-CLI plan depends on.

---

## File Structure

- Modify: `src/agent_team/cli_registry.py` — add `teammate_launch_args: tuple[str, ...] = ()` to `CliSpec`; set codex's value. **(D12)**
- Modify: `src/agent_team/psmux_backend.py` — add `capture_pane(target) -> str` **(D11)** and `pipe_pane(target, log_path) -> None` **(D10)**.
- Modify: `src/agent_team/teammate_runner.py` — import `get_cli_spec` + `time`; add `_READY_*` constants + `_wait_until_input_ready`; rewrite the non-mock branch of `spawn` to apply launch args (D12), pipe the pane (D10), wait for readiness (D11), then kickoff.
- Modify: `tests/conftest.py` — autouse fixture forcing fast readiness constants so spawn-calling tests don't wait the real timeout.
- Modify: `src/agent_team/cli/logs.py` — `logs export` writes a bundle directory (events.jsonl + transcripts/<name>.log). **(D10)**
- Test: `tests/unit/test_cli_registry.py`, `tests/unit/test_psmux_backend.py`, `tests/unit/test_teammate_runner.py`, `tests/unit/test_cli_logs.py`.
- New: `tests/manual/s11b-teammate-hardening.md` (live checklist). Docs: `PROGRESS.md`.

**Task order & dependencies:** Task 1 (registry), Task 2 (`capture_pane`), Task 3 (`pipe_pane`) are independent primitives. Task 4 (`spawn` wiring) depends on all three. Task 5 (logs) depends on Task 3's transcript path convention. Task 6 last.

---

## Task 1: D12 — registry `teammate_launch_args`

**Files:**
- Modify: `src/agent_team/cli_registry.py`
- Test: `tests/unit/test_cli_registry.py`

- [ ] **Step 1: Write the failing test**

In `tests/unit/test_cli_registry.py`, add (import `get_cli_spec` is present; add `CliSpec` import if you assert the default):

```python
def test_codex_teammate_launch_args_bypass() -> None:
    from agent_team.cli_registry import get_cli_spec

    codex = get_cli_spec("codex")
    # D12: codex teammate runs hands-off (no per-command approval / sandbox /
    # trust prompts) — applied by the runner, never named by the lead.
    assert codex.teammate_launch_args == ("--dangerously-bypass-approvals-and-sandbox",)


def test_claude_teammate_launch_args_empty() -> None:
    from agent_team.cli_registry import get_cli_spec

    # claude teammate launches bare (CLI-neutral invariant; no per-CLI flags).
    assert get_cli_spec("claude").teammate_launch_args == ()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/unit/test_cli_registry.py::test_codex_teammate_launch_args_bypass -v`
Expected: FAIL — `CliSpec` has no `teammate_launch_args` attribute (`AttributeError`).

- [ ] **Step 3: Add the field + codex value**

In `src/agent_team/cli_registry.py`, add the field to `CliSpec` (after `mcp_config_filename`, currently line 30):

```python
    mcp_config_filename: str | None
    # Per-CLI args the RUNNER appends to a teammate's bare launch command (read
    # from here, never from the lead — preserves lead/teammate CLI decoupling).
    # codex: run non-interactively (no per-command approval, no sandbox, no trust
    # prompt) so a teammate pane works hands-off. claude: none (bare launch).
    teammate_launch_args: tuple[str, ...] = ()
```

Then set codex's value in `_REGISTRY` (currently lines 48-53):

```python
    "codex": CliSpec(
        name="codex",
        supports_lead=False,
        supports_teammate=True,
        mcp_config_filename=None,
        teammate_launch_args=("--dangerously-bypass-approvals-and-sandbox",),
    ),
```

(claude needs no change — the default `()` applies.)

- [ ] **Step 4: Run the targeted + existing registry tests**

Run: `python -m pytest tests/unit/test_cli_registry.py -v`
Expected: PASS — new tests green; existing registry tests unaffected (the new field has a default, so the frozen `CliSpec` stays hashable and the claude/codex entries still construct).

- [ ] **Step 5: Commit**

```bash
git add src/agent_team/cli_registry.py tests/unit/test_cli_registry.py
git commit -m "feat(s11b): D12 registry teammate_launch_args (codex hands-off)

Add CliSpec.teammate_launch_args; codex teammate gets
--dangerously-bypass-approvals-and-sandbox so its pane runs non-interactively
(no per-command approval / sandbox / trust prompts). Read by the runner from the
registry, never named by the lead — keeps lead/teammate CLI decoupling.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: D11 — `PsmuxBackend.capture_pane`

**Files:**
- Modify: `src/agent_team/psmux_backend.py`
- Test: `tests/unit/test_psmux_backend.py`

- [ ] **Step 1: Write the failing test**

In `tests/unit/test_psmux_backend.py`, add (match the file's existing import of `PsmuxBackend`):

```python
def test_capture_pane_mock_records_argv_and_returns_empty() -> None:
    backend = PsmuxBackend(mock=True)
    out = backend.capture_pane("%3")
    assert out == ""
    call = next(c for c in backend.recorded_calls if "capture-pane" in c.args)
    assert call.args == ["capture-pane", "-t", "%3", "-p"]


def test_capture_pane_rejects_bad_target() -> None:
    from agent_team._io import InvalidPathSegmentError

    backend = PsmuxBackend(mock=True)
    with pytest.raises(InvalidPathSegmentError):
        backend.capture_pane("%bad!")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/unit/test_psmux_backend.py -k capture_pane -v`
Expected: FAIL — `PsmuxBackend` has no `capture_pane` method (`AttributeError`).

- [ ] **Step 3: Add `capture_pane`**

In `src/agent_team/psmux_backend.py`, add after `list_panes` (currently ends line 185):

```python
    def capture_pane(self, target: str) -> str:
        """Return the current pane buffer text (`capture-pane -p`).

        Used by the runner's input-readiness wait (D11). In mock mode there is no
        real pane, so this returns "" — callers must treat empty as "not ready
        yet" and fall back to a timeout, which the mock path exercises.
        """
        safe_target = self._validate_target(target)
        return self._run(["capture-pane", "-t", safe_target, "-p"])
```

- [ ] **Step 4: Run the targeted + existing psmux tests**

Run: `python -m pytest tests/unit/test_psmux_backend.py -v`
Expected: PASS — new tests green; existing psmux tests unaffected.

- [ ] **Step 5: Commit**

```bash
git add src/agent_team/psmux_backend.py tests/unit/test_psmux_backend.py
git commit -m "feat(s11b): D11 PsmuxBackend.capture_pane

Add capture-pane wrapper returning the pane buffer text, for the teammate
input-readiness wait. Mock mode returns '' (exercises the timeout fallback).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: D10 — `PsmuxBackend.pipe_pane`

**Files:**
- Modify: `src/agent_team/psmux_backend.py`
- Test: `tests/unit/test_psmux_backend.py`

- [ ] **Step 1: Write the failing test**

In `tests/unit/test_psmux_backend.py`, add:

```python
def test_pipe_pane_mock_records_argv_with_log_path(tmp_path: Path) -> None:
    backend = PsmuxBackend(mock=True)
    log = tmp_path / "transcript.log"
    backend.pipe_pane("%2", log)
    call = next(c for c in backend.recorded_calls if "pipe-pane" in c.args)
    assert call.args[:4] == ["pipe-pane", "-t", "%2", "-o"]
    # The redirect command names the absolute log path (forward-slash form so the
    # pane shell does not mangle Windows backslashes) so the transcript lands in
    # the session dir regardless of the pane's cwd.
    assert log.resolve().as_posix() in call.args[4]


def test_pipe_pane_rejects_bad_target(tmp_path: Path) -> None:
    from agent_team._io import InvalidPathSegmentError

    backend = PsmuxBackend(mock=True)
    with pytest.raises(InvalidPathSegmentError):
        backend.pipe_pane("not-a-pane!", tmp_path / "t.log")
```

(Ensure `from pathlib import Path` is imported at the top of the test file.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/unit/test_psmux_backend.py -k pipe_pane -v`
Expected: FAIL — `PsmuxBackend` has no `pipe_pane` method (`AttributeError`).

- [ ] **Step 3: Add `pipe_pane`**

In `src/agent_team/psmux_backend.py`, add after `capture_pane`:

```python
    def pipe_pane(self, target: str, log_path: Path) -> None:
        """Stream the pane's output to `log_path` (`pipe-pane -o <cmd>`) (D10).

        Gives each teammate a durable transcript of its real work (events.jsonl
        and mail only hold coordination). The redirect command appends the pane
        stream to the absolute log path; the pane's shell runs it, so the exact
        portability of `cat >>` is verified live (see tests/manual). The log path
        is resolved so it lands in the session dir no matter the pane cwd.
        """
        safe_target = self._validate_target(target)
        # as_posix() so the path uses forward slashes: a Windows backslash path
        # (C:\Users\...\t.log) inside the double-quoted redirect would be mangled
        # by the pane shell's escape handling. Forward slashes are accepted by
        # cmd.exe/PowerShell and unix shells alike. (Whether `cat` itself exists
        # in the pane's shell is verified live — see tests/manual.)
        redirect = f'cat >> "{log_path.resolve().as_posix()}"'
        self._run(["pipe-pane", "-t", safe_target, "-o", redirect])
```

- [ ] **Step 4: Run the targeted + existing psmux tests**

Run: `python -m pytest tests/unit/test_psmux_backend.py -v`
Expected: PASS — new tests green; existing tests unaffected.

- [ ] **Step 5: Commit**

```bash
git add src/agent_team/psmux_backend.py tests/unit/test_psmux_backend.py
git commit -m "feat(s11b): D10 PsmuxBackend.pipe_pane

Add pipe-pane wrapper that streams a pane to an absolute log path, for durable
per-teammate transcripts. Redirect command portability verified live (manual).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: D10+D11+D12 — wire `TeammateRunner.spawn`

**Files:**
- Modify: `src/agent_team/teammate_runner.py`
- Modify: `tests/conftest.py` (autouse fast-readiness fixture)
- Test: `tests/unit/test_teammate_runner.py`

**Depends on Tasks 1, 2, 3.**

- [ ] **Step 1: Add the autouse fast-readiness fixture (prevents slow tests)**

> **Implement Step 4 (imports, readiness constants + helper) BEFORE this step.** This
> fixture `monkeypatch.setattr`s the `_READY_*` constants, which Step 4 defines; if you
> add the fixture first, test collection fails with `AttributeError` (monkeypatch raises
> when the target attribute is absent).

The new readiness wait would otherwise block every spawn-calling test for the real
timeout (mock `capture_pane` returns "" → no settle → fallback). Add to `tests/conftest.py`
(near the other fixtures):

```python
@pytest.fixture(autouse=True)
def _fast_teammate_readiness(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the D11 input-readiness wait near-instant in unit tests.

    Mock psmux returns "" from capture_pane (never 'settles'), so spawn would
    otherwise burn the full real timeout per call. These tiny values make the
    fallback fire immediately; the real timing is exercised in tests/manual.
    """
    from agent_team import teammate_runner

    monkeypatch.setattr(teammate_runner, "_READY_POLL_INTERVAL_S", 0.0)
    monkeypatch.setattr(teammate_runner, "_READY_MAX_WAIT_S", 0.02)
    monkeypatch.setattr(teammate_runner, "_READY_SETTLE_COUNT", 1)
```

(`pytest` is already imported in conftest.py. All three constants are patched so the
fixture fully isolates tests from the production timing, not just two of them.)

- [ ] **Step 2: Write the failing tests**

In `tests/unit/test_teammate_runner.py`, add:

```python
def test_wait_until_input_ready_settles_then_returns_true() -> None:
    from agent_team.teammate_runner import _wait_until_input_ready

    class _FakeCapture:
        def __init__(self, frames: list[str]) -> None:
            self._frames = frames
            self.calls = 0

        def capture_pane(self, target: str) -> str:
            frame = self._frames[min(self.calls, len(self._frames) - 1)]
            self.calls += 1
            return frame

    fake = _FakeCapture(["", "banner ready", "banner ready"])
    ready = _wait_until_input_ready(
        fake, "%1", poll_interval=0.0, max_wait=5.0, settle_count=2
    )
    assert ready is True
    assert fake.calls == 3  # empty, then two identical non-empty


def test_wait_until_input_ready_times_out_returns_false() -> None:
    from agent_team.teammate_runner import _wait_until_input_ready

    class _NeverReady:
        def capture_pane(self, target: str) -> str:
            return ""

    ready = _wait_until_input_ready(
        _NeverReady(), "%1", poll_interval=0.0, max_wait=0.02, settle_count=2
    )
    assert ready is False


def test_spawn_pipes_transcript_waits_then_kickoffs(
    runner: TeammateRunner,
    psmux_backend: PsmuxBackend,
    tmp_path: Path,
) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    runner.spawn(**_spawn_kwargs(session_dir=session_dir, project_path=project))

    calls = psmux_backend.recorded_calls
    # D10: the pane is piped to the teammate's transcript.log (forward-slash path).
    pipe = next(c for c in calls if "pipe-pane" in c.args)
    transcript = (session_dir / "teammates" / "helper-1" / "transcript.log").resolve()
    assert transcript.as_posix() in pipe.args[4]
    # D11: readiness was polled (capture-pane) before the kickoff was sent.
    assert any("capture-pane" in c.args for c in calls)

    def first_index(kind: str) -> int:
        return next(i for i, c in enumerate(calls) if kind in c.args)

    # Ordering: split-window → pipe-pane → capture-pane → send-keys.
    assert first_index("split-window") < first_index("pipe-pane")
    assert first_index("pipe-pane") < first_index("capture-pane")
    assert first_index("capture-pane") < first_index("send-keys")

    # Regression: a claude teammate gets NO codex bypass flag (launch_args == ()).
    split = next(c for c in calls if "split-window" in c.args)
    assert "--dangerously-bypass-approvals-and-sandbox" not in " ".join(split.args)


def test_spawn_codex_applies_bypass_launch_args(
    runner: TeammateRunner,
    psmux_backend: PsmuxBackend,
    tmp_path: Path,
) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    # 'implementer' persona has cli: codex (bundled).
    runner.spawn(
        **_spawn_kwargs(
            session_dir=session_dir,
            project_path=project,
            teammate_name="helper-impl",
            persona="implementer",
        )
    )
    split = next(c for c in psmux_backend.recorded_calls if "split-window" in c.args)
    joined = " ".join(split.args)
    # D12: codex teammate launched non-interactively, args from the registry.
    assert "codex" in joined
    assert "--dangerously-bypass-approvals-and-sandbox" in joined
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python -m pytest tests/unit/test_teammate_runner.py -k "wait_until_input_ready or pipes_transcript or bypass_launch_args" -v`
Expected: FAIL — `_wait_until_input_ready` does not exist; spawn issues no pipe-pane/capture-pane and codex launch has no bypass flag.

- [ ] **Step 4: Add imports, readiness constants + helper**

In `src/agent_team/teammate_runner.py`, update the imports block (top of file):

```python
import time
from dataclasses import dataclass
from pathlib import Path

from agent_team._io import format_ts, utc_now
from agent_team.bundled_paths import render_bundled_template
from agent_team.cli_registry import get_cli_spec
from agent_team.personas import PersonaRegistry
from agent_team.psmux_backend import PsmuxBackend
```

Then, after `_MOCK_COMMAND` (currently line 13), add:

```python
# D11 input-readiness tuning. The teammate CLI is not reading stdin the instant
# its pane is split, so an eager kickoff drops. Poll the pane until its output
# settles (CLI at its input prompt), then send. Tests patch these to be instant.
_READY_POLL_INTERVAL_S = 0.25
_READY_MAX_WAIT_S = 8.0
_READY_SETTLE_COUNT = 2


def _wait_until_input_ready(
    psmux: object,
    pane_id: str,
    *,
    poll_interval: float,
    max_wait: float,
    settle_count: int,
) -> bool:
    """Block until the teammate CLI pane looks ready for input, or max_wait (D11).

    CLI-neutral heuristic: capture the pane repeatedly; once its output is
    non-empty and unchanged across `settle_count` consecutive polls, the CLI has
    finished its startup banner and is at its input prompt. Returns True if it
    settled, False on timeout — the caller sends the kickoff either way (the
    fallback covers CLIs whose output never fully settles).
    """
    prev: str | None = None
    same = 0
    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline:
        cur = psmux.capture_pane(pane_id)
        if cur and cur == prev:
            same += 1
            if same >= settle_count:
                return True
        else:
            same = 1 if cur else 0
        prev = cur
        time.sleep(poll_interval)
    return False
```

- [ ] **Step 5: Rewrite the non-mock branch of `spawn`**

In `src/agent_team/teammate_runner.py`, replace the `else:` branch of `spawn`
(currently lines 95-121, from `teammate_dir = …` through the `send_keys(...)` call) with:

```python
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
            # D12: per-CLI launch args from the registry (e.g. codex non-interactive
            # approval/sandbox bypass). Read by the RUNNER, never named by the lead.
            launch_args = get_cli_spec(p.cli).teammate_launch_args
            command = " ".join([p.cli, *launch_args])
            # Run the teammate CLI from the project root so relative file edits,
            # pytest, and git target the real checkout.
            pane_id = self.psmux.split_pane(
                psmux_session, command=command, cwd=project_path
            )
            # D10: capture the pane's full output to a durable per-teammate
            # transcript (coordination events + mail do NOT capture its work).
            transcript_path = teammate_dir / "transcript.log"
            self.psmux.pipe_pane(pane_id, transcript_path)
            # D11: wait until the CLI is reading stdin before the kickoff, else
            # the first keystrokes drop during CLI startup.
            _wait_until_input_ready(
                self.psmux,
                pane_id,
                poll_interval=_READY_POLL_INTERVAL_S,
                max_wait=_READY_MAX_WAIT_S,
                settle_count=_READY_SETTLE_COUNT,
            )
            # Trigger with a single-line kickoff pointing at the absolute brief path.
            self.psmux.send_keys(
                pane_id, _kickoff_line(teammate_name, brief_path.resolve()), enter=True
            )
```

- [ ] **Step 6: Run the teammate-runner suite**

Run: `python -m pytest tests/unit/test_teammate_runner.py -v`
Expected: PASS — the new tests green; the existing tests
(`test_spawn_splits_pane_and_sends_persona_prompt`, `test_spawn_renders_agents_md_per_teammate`,
`test_spawn_passes_persona_cli_to_split_pane`, `test_spawn_mock_*`) still pass: claude's
`launch_args` is `()` so `" ".join(["claude"])` == `"claude"` (split args unchanged), the
`next(... "split-window" ...)` / `next(... "send-keys" ...)` selectors still find their calls,
and mock mode still skips the entire else branch (no pipe/capture/send, no `teammates/` dir).
The autouse fixture keeps the readiness wait instant.

- [ ] **Step 7: Run the full suite to catch orchestrator-level spawn tests**

Run: `python -m pytest tests/ -q`
Expected: PASS — orchestrator spawn tests (which build `TeammateRunner(..., mock=False)` with mock psmux) also stay fast via the autouse fixture and unaffected by the new calls.

- [ ] **Step 8: Commit**

```bash
git add src/agent_team/teammate_runner.py tests/conftest.py tests/unit/test_teammate_runner.py
git commit -m "feat(s11b): wire teammate spawn — transcript + readiness + launch args

TeammateRunner.spawn now: applies registry teammate_launch_args (D12 codex
hands-off), pipes the pane to transcript.log (D10), and waits for CLI input-
readiness via capture-pane settle before the kickoff (D11). All inside the
runner — the lead still only names a persona (CLI-decoupling invariant intact).
Autouse fixture keeps the readiness wait instant in unit tests.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: D10 — `logs export` bundles transcripts + events

**Files:**
- Modify: `src/agent_team/cli/logs.py`
- Test: `tests/unit/test_cli_logs.py`

- [ ] **Step 1: Update the export test for the bundle layout**

Replace the export assertions in `tests/unit/test_cli_logs.py::test_logs_tail_and_export`
(currently lines 32-40) with a bundle-directory check, and seed a transcript:

```python
    # Seed a teammate transcript so export bundles it alongside events.
    transcript = session_store.session_dir("cli-logs") / "teammates" / "helper-1" / "transcript.log"
    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_text("teammate did work\n", encoding="utf-8")

    dest = tmp_path / "bundle"
    export = runner.invoke(
        main,
        ["logs", "export", "--session", "cli-logs", "--to", str(dest)],
        env=cli_env,
    )
    assert export.exit_code == 0
    events_out = dest / "events.jsonl"
    assert events_out.exists()
    assert "mail_sent" in events_out.read_text(encoding="utf-8")
    transcript_out = dest / "transcripts" / "helper-1.log"
    assert transcript_out.exists()
    assert "teammate did work" in transcript_out.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/unit/test_cli_logs.py::test_logs_tail_and_export -v`
Expected: FAIL — current `export` copies events to a single file (`--to` is a file), so `dest/events.jsonl` and `dest/transcripts/helper-1.log` do not exist.

- [ ] **Step 3: Rewrite `export_cmd` to produce a bundle directory**

In `src/agent_team/cli/logs.py`, replace `export_cmd` (currently lines 53-69) with:

```python
@logs_group.command("export")
@click.option("--session", required=True)
@click.option("--to", "dest", required=True, type=click.Path(path_type=Path))
def export_cmd(session: str, dest: Path) -> None:
    """Export a session bundle: events.jsonl + each teammate's transcript."""
    try:
        session_dir = resolve_session_dir(session)
        dest.mkdir(parents=True, exist_ok=True)

        events_src = session_dir / "events.jsonl"
        events_dst = dest / "events.jsonl"
        if events_src.exists():
            shutil.copy2(events_src, events_dst)
        else:
            events_dst.write_text("", encoding="utf-8")

        teammates_dir = session_dir / "teammates"
        if teammates_dir.is_dir():
            transcripts_dst = dest / "transcripts"
            for member_dir in sorted(teammates_dir.iterdir()):
                transcript = member_dir / "transcript.log"
                if transcript.exists():
                    transcripts_dst.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(transcript, transcripts_dst / f"{member_dir.name}.log")

        click.echo(str(dest))
    except CLI_ERRORS as exc:
        echo_error(str(exc))
```

- [ ] **Step 4: Run the targeted + existing logs tests**

Run: `python -m pytest tests/unit/test_cli_logs.py -v`
Expected: PASS — the updated export test green; `test_logs_follow_once` and `logs tail` unaffected (only `export` changed).

- [ ] **Step 5: Commit**

```bash
git add src/agent_team/cli/logs.py tests/unit/test_cli_logs.py
git commit -m "feat(s11b): D10 logs export bundles events + teammate transcripts

logs export --to <dir> now writes a bundle: events.jsonl plus
transcripts/<name>.log for each teammate with a captured transcript.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Manual checklist + PROGRESS + verify

**Files:**
- New: `tests/manual/s11b-teammate-hardening.md`
- Modify: `PROGRESS.md`

- [ ] **Step 1: Write the live-verification checklist**

Create `tests/manual/s11b-teammate-hardening.md` (match the style of the existing
`tests/manual/s10-payment-api-e2e.md`). It must cover the three live behaviors the
unit tests deliberately do NOT cover (psmux is mocked):

```markdown
# S11b manual checklist — teammate hardening (D10/D11/D12)

Run on the Windows box with real psmux + real CLIs. Unit tests cover the argv
seam; these confirm the live behavior.

## D10 — transcript capture (pipe-pane)
- [ ] Start a session, spawn a claude teammate. Confirm
      `{session_dir}/teammates/<name>/transcript.log` is created AND grows as the
      teammate prints output. (Verifies `cat >> "<path>"` runs under psmux on Windows.)
- [ ] If the redirect command does not work on Windows psmux (e.g. the pane shell
      is cmd.exe, which has no `cat`), note the actual shell the pane uses and the
      working redirect form here: ____________________  Then update
      `PsmuxBackend.pipe_pane`'s `redirect` to the working command BEFORE relying on
      transcripts — the unit test only covers the argv seam, not live capture.
- [ ] `agent-team logs export --session <id> --to <dir>` produces
      `<dir>/events.jsonl` and `<dir>/transcripts/<name>.log`.

## D11 — kickoff input-readiness
- [ ] Spawn a codex teammate (slow first-run startup). Confirm the kickoff is NOT
      dropped — the teammate reads its brief and goes `teammate_ready` without a
      manual re-send. (Pre-D11 this dropped the first keystrokes.)
- [ ] Confirm the readiness wait adds no noticeable delay for a fast claude teammate.

## D12 — codex non-interactive
- [ ] Spawn a codex teammate; confirm it runs commands WITHOUT prompting for
      per-command approval and WITHOUT the first-run trust prompt (launched with
      --dangerously-bypass-approvals-and-sandbox).
- [ ] Confirm the lead never saw/issued any codex flag (decoupling invariant).
```

- [ ] **Step 2: Add the S11b entry to PROGRESS.md**

In `PROGRESS.md`, add an S11b "done" entry summarizing D10 (transcript capture +
logs bundle), D11 (capture-pane input-readiness), D12 (registry-driven codex
hands-off launch), noting the manual checklist for live verification. Match the
existing entry style.

- [ ] **Step 3: Full verification**

Run: `python -m pytest tests/ -q`
Expected: PASS — S11a's 227 + the S11b additions (D12×2, capture_pane×2, pipe_pane×2, spawn-wiring×4, logs×0-new(updated), readiness-helper covered in spawn-wiring ≈ +10).

Run: `python -m ruff check src/ tests/`
Expected: `All checks passed!`

Confirm the full suite ran in a normal time (no test stuck on the readiness timeout — proves the autouse fixture works).

- [ ] **Step 4: Commit**

```bash
git add tests/manual/s11b-teammate-hardening.md PROGRESS.md
git commit -m "docs(s11b): manual checklist + PROGRESS S11b done

Live-verification checklist for the mocked-in-unit behaviors (pipe-pane
transcript on Windows, codex no-approval run, capture-pane readiness) and the
S11b PROGRESS entry (D10/D11/D12).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage (docs/s11-multi-cli-plan.md):**
- **D10** (teammate transcript capture) → Task 3 (`pipe_pane`) + Task 4 (wire at spawn) + Task 5 (`logs export` bundles). Transcript never enters lead context (it's on disk, D6). ✓
- **D11** (kickoff input-readiness, CLI-neutral, scope = one-time kickoff drop only) → Task 2 (`capture_pane`) + Task 4 (`_wait_until_input_ready` + wire). Does not touch the async teammate_ready handshake. ✓
- **D12** (codex teammate non-interactive, registry-driven `teammate_launch_args`, applied by runner not lead) → Task 1 (registry) + Task 4 (apply in spawn). ✓
- Touch-points (`cli_registry.py` D12 field; `teammate_runner.py`/`cli/logs.py` D10; `teammate_runner.py` D11) → all covered. ✓
- Decoupling invariant (lead names only a persona; runner reads registry) → preserved; guarded explicitly. ✓

**2. Placeholder scan:** No TBD/TODO; every code step shows complete code. Task 6 checklist/PROGRESS are prose-by-design (manual artifacts), not code placeholders. ✓

**3. Type consistency:**
- `CliSpec.teammate_launch_args: tuple[str, ...] = ()` defined Task 1; read via `get_cli_spec(p.cli).teammate_launch_args` Task 4. ✓
- `capture_pane(target) -> str` (Task 2) called by `_wait_until_input_ready` (Task 4) and in `spawn`. `pipe_pane(target, log_path: Path)` (Task 3) called in `spawn` (Task 4). ✓
- `_wait_until_input_ready(psmux, pane_id, *, poll_interval, max_wait, settle_count) -> bool` (Task 4) called in `spawn` with the `_READY_*` constants; tests call it directly with explicit params + a stub exposing `capture_pane`. ✓
- `_READY_POLL_INTERVAL_S`/`_READY_MAX_WAIT_S`/`_READY_SETTLE_COUNT` defined Task 4; patched by the autouse fixture (Task 4 Step 1). ✓

## Expert review axes

Plan-review (before implement, BLOCKING=0) and code-review (after, BLOCKING+P1) candidate axes:
- **E1 Registry/API** — `teammate_launch_args` shape (tuple, frozen-dataclass hashability), command composition `" ".join([cli, *args])`, no lead leakage.
- **E2 psmux backend** — `capture_pane`/`pipe_pane` argv correctness, target validation, the `pipe-pane -o "cat >> …"` portability risk (Windows), mock semantics.
- **E3 Readiness logic** — `_wait_until_input_ready` settle/timeout correctness, no busy-spin pathology, the autouse fast fixture (does it make all spawn tests fast without hiding bugs?), no double-submit.
- **E4 Tests** — coverage (settle vs timeout, transcript+ordering, codex bypass, logs bundle), isolation, existing-test regressions from extra recorded calls.
- **E5 Decoupling invariant + observability** — confirm the lead never names a CLI/flag; transcript never enters lead context; logs bundle is complete.
