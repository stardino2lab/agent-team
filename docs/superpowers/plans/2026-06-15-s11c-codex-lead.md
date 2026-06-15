# S11c — codex as 2nd verified lead (D1 + D2 + D3 + D4): Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `codex` a launchable second lead CLI — flip `config.yaml: lead_cli: codex` and the orchestrator builds a real `codex exec` lead pane that connects to the agent-team MCP server — proving the CLI-neutral lead seam and giving the cost dial (revert = one-line flip).

**Architecture:** Generalize the two hardcoded-for-claude orchestrator seams into per-CLI dispatch keyed on `CliSpec`, and register codex as lead-capable. **D3/D4:** `cli_registry` gains `mcp_format` and flips codex `supports_lead=True`. **D2:** `_write_lead_mcp_config` becomes format-dispatched — claude → a JSON file (`--mcp-config`); codex → a **TOML profile** written to `{CODEX_HOME}/agent-team-<sid>.config.toml`, loaded via `codex exec --ignore-user-config --profile agent-team-<sid>`. **D1:** `_build_lead_launch_command` gains a codex `elif` building that `codex exec` line. The lead system prompt rides codex's working-root **AGENTS.md** (`{session_dir}/lead/AGENTS.md` + `-C`), since codex has no `--append-system-prompt-file`. **D4:** `lead_cli` is already read from config in `start()`; codex just becomes a valid value. Reference spec: `docs/s11-multi-cli-plan.md` (decisions **D1–D4**, "Lead launch — codex branch (sketch)").

**Tech Stack:** Python 3.12, pytest, ruff, `tomllib` (stdlib, read-only — used in tests to assert the rendered profile parses). psmux mocked. The live codex-as-lead E2E (does codex actually launch, load the profile, connect MCP, and orchestrate autonomously) is **not** auto-tested — it spends tokens and needs the real binary; it is a `tests/manual/` checklist (Task 5), per the project's live-test policy. This plan delivers the unit-tested launch-line/profile **construction** seam.

---

## Design decisions resolved before this plan (user-confirmed + codex-verified)

1. **codex MCP injection = a CODEX_HOME profile** (`--profile`), NOT inline `-c`. codex has no flag to load an arbitrary config-file path; inline `-c` values (containing `=`, `"`, `[`, `]`, spaces from `Program Files`, backslashes) are unsafe to type into a Windows pane shell (PowerShell vs cmd quoting differs). A profile keeps only a shell-safe NAME on the command line. The profile file lives in `{CODEX_HOME}/agent-team-<sid>.config.toml`; `--ignore-user-config` skips the user's base `config.toml` for isolation while auth still resolves from `CODEX_HOME`. *(Live-verify that `--ignore-user-config` + `--profile` still layers the profile — Task 5.)*
2. **codex lead = `codex exec` autonomous** (spec D3). The lead runs non-interactively: codex orchestrates via MCP (spawn/mail/wait) until done, then exits. The user approves spawns via the TUI queue (cannot chat with it like the claude lead). This is a deliberate property of a codex lead.
3. **codex lead system prompt = working-root AGENTS.md.** `build_lead_context.text` (incl. the D6 preamble) → `{session_dir}/lead/AGENTS.md`; `codex exec -C "{session_dir}/lead"` makes that the working root so codex reads it. cwd outside the project ⇒ `--skip-git-repo-check`. A short bootstrap PROMPT arg points codex at it. The project's own AGENTS.md is NOT read (working root is the session lead dir, not the project).
4. **D2 file deviation (documented):** the spec touch-points said codex `mcp_config_filename="codex-mcp.toml"` in the session dir. Reality: codex profiles MUST live in `CODEX_HOME` and are named `<profile>.config.toml`. So codex's registry `mcp_config_filename` stays `None`; `mcp_format="toml"` drives the profile renderer; the file path is derived (`{CODEX_HOME}/agent-team-<sid>.config.toml`). The CliSpec invariant changes from "lead requires `mcp_config_filename`" to "lead requires `mcp_format`; `json` format requires `mcp_config_filename`".

## Invariant guard (do NOT break)

This is a LEAD-launch change only. The teammate path (CLI-decoupling invariant) is untouched: the lead is still launched by the Python orchestrator from `config.lead_cli`; teammates are still spawned by persona via the runner. Nothing here lets a lead name a teammate's CLI.

---

## File Structure

- Modify: `src/agent_team/cli_registry.py` — add `mcp_format: str | None`; change the `__post_init__` invariant; flip codex `supports_lead=True`, `mcp_format="toml"`; claude `mcp_format="json"`. **(D3/D4)**
- Modify: `src/agent_team/orchestrator.py` — add `os` import; `_codex_home`, `_codex_profile_name`, `_lead_mcp_server_config`, `_render_codex_profile_toml`, `_write_codex_lead_agents_md` helpers + `_CODEX_LEAD_BOOTSTRAP` const; format-dispatch `_write_lead_mcp_config` **(D2)**; add codex `elif` to `_build_lead_launch_command` **(D1/D3)**; format-aware launch wiring + profile cleanup in `start()` **(D4)**.
- Test: `tests/unit/test_cli_registry.py`, `tests/unit/test_orchestrator.py`.
- New: `tests/manual/s11c-codex-lead.md`. Docs: `PROGRESS.md`, `docs/s11-multi-cli-plan.md` (touch-points note for the profile deviation).

**Task order:** Task 1 (registry) → Task 2 (`_write_lead_mcp_config` dispatch + helpers) → Task 3 (`_build_lead_launch_command` codex) → Task 4 (`start()` wiring + update the 2 existing parametrized tests) → Task 5 (docs/manual/verify).

---

## Task 1: D3/D4 — registry `mcp_format` + codex lead-capable

**Files:**
- Modify: `src/agent_team/cli_registry.py`
- Test: `tests/unit/test_cli_registry.py`

- [ ] **Step 1: Write the failing tests**

In `tests/unit/test_cli_registry.py`, add:

```python
def test_codex_is_lead_capable_with_toml_format() -> None:
    from agent_team.cli_registry import get_cli_spec, is_lead_supported

    codex = get_cli_spec("codex")
    assert codex.supports_lead is True
    assert codex.mcp_format == "toml"
    # codex uses a CODEX_HOME profile, not a session-dir file.
    assert codex.mcp_config_filename is None
    assert is_lead_supported("codex") is True


def test_claude_lead_uses_json_format() -> None:
    from agent_team.cli_registry import get_cli_spec

    claude = get_cli_spec("claude")
    assert claude.mcp_format == "json"
    assert claude.mcp_config_filename == "claude-mcp.json"


def test_cli_spec_lead_requires_mcp_format() -> None:
    from agent_team.cli_registry import CliSpec

    import pytest

    with pytest.raises(ValueError, match="mcp_format"):
        CliSpec(
            name="x",
            supports_lead=True,
            supports_teammate=False,
            mcp_config_filename=None,
            mcp_format=None,
        )
```

> The json-format-requires-filename invariant is covered by the EXISTING
> `test_post_init_rejects_lead_without_filename`, which Step 3b updates to pass
> `mcp_format="json"` (do not add a duplicate test for it).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/unit/test_cli_registry.py -k "lead_capable_with_toml or json_format or lead_requires_mcp_format or json_format_requires" -v`
Expected: FAIL — `CliSpec` has no `mcp_format`; codex `supports_lead` is False.

- [ ] **Step 3: Add `mcp_format` + change the invariant**

In `src/agent_team/cli_registry.py`, replace the `CliSpec` dataclass body (currently lines 25-38) with:

```python
@dataclass(frozen=True)
class CliSpec:
    name: str
    supports_lead: bool
    supports_teammate: bool
    mcp_config_filename: str | None
    teammate_launch_args: tuple[str, ...] = ()
    # How the lead MCP config is delivered: "json" (a file passed via
    # --mcp-config, claude) or "toml" (a CODEX_HOME profile loaded via --profile,
    # codex). Required for any lead-capable CLI.
    mcp_format: str | None = None

    def __post_init__(self) -> None:
        if self.supports_lead and not self.mcp_format:
            raise ValueError(
                f"{self.name}: supports_lead=True requires mcp_format"
            )
        if self.mcp_format == "json" and not self.mcp_config_filename:
            raise ValueError(
                f"{self.name}: mcp_format='json' requires mcp_config_filename"
            )
        if not (self.supports_lead or self.supports_teammate):
            raise ValueError(f"{self.name}: must support at least one role")
```

> NOTE: `teammate_launch_args` (added in S11b) keeps its position before `mcp_format`; both are defaulted fields, so the codex entry must set them by keyword.

Then update `_REGISTRY` (currently lines 41-55):

```python
_REGISTRY: dict[str, CliSpec] = {
    "claude": CliSpec(
        name="claude",
        supports_lead=True,
        supports_teammate=True,
        mcp_config_filename="claude-mcp.json",
        mcp_format="json",
    ),
    "codex": CliSpec(
        name="codex",
        supports_lead=True,
        supports_teammate=True,
        mcp_config_filename=None,
        teammate_launch_args=("--dangerously-bypass-approvals-and-sandbox",),
        mcp_format="toml",
    ),
    # antigravity/gemini: S12 — added with persona YAML + (for lead) launch builder.
}
```

- [ ] **Step 3b: Update the EXISTING registry tests + module docstring made stale by the flip**

Three existing things in `tests/unit/test_cli_registry.py` encode the old "codex is teammate-only / lead requires a filename" truth and WILL fail; fix them:

1. `test_spec_invariant` (the `_REGISTRY`-parametrized test) — replace its `supports_lead` block so the invariant matches the new rule (lead requires `mcp_format`; only `json` requires a filename):

```python
    assert spec.name == name
    if spec.supports_lead:
        assert spec.mcp_format is not None
    if spec.mcp_format == "json":
        assert spec.mcp_config_filename is not None
    assert spec.supports_lead or spec.supports_teammate
```

2. `test_codex_is_teammate_only` — rename + flip to the new truth:

```python
def test_codex_is_lead_and_teammate() -> None:
    spec = get_cli_spec("codex")
    assert spec.supports_lead is True
    assert spec.supports_teammate is True
    assert spec.mcp_format == "toml"
    # codex uses a CODEX_HOME profile, not a session-dir file.
    assert spec.mcp_config_filename is None
```

3. `test_post_init_rejects_lead_without_filename` — under the new invariant a lead with `mcp_format=None` raises "mcp_format", not "mcp_config_filename". Re-point this test at the json-requires-filename path by passing `mcp_format="json"` (keeps the `match="mcp_config_filename"` assertion valid):

```python
def test_post_init_rejects_lead_without_filename() -> None:
    with pytest.raises(ValueError, match="mcp_config_filename"):
        CliSpec(
            name="bogus",
            supports_lead=True,
            supports_teammate=False,
            mcp_config_filename=None,
            mcp_format="json",
        )
```

4. Update the `cli_registry.py` module docstring (line ~6): change "codex (teammate only)" → "codex (lead + teammate)" and the "antigravity is planned for S11+" line → "S12".

- [ ] **Step 4: Run the targeted + full registry tests**

Run: `python -m pytest tests/unit/test_cli_registry.py -v`
Expected: PASS — the new `test_codex_is_lead_capable_with_toml_format`/`test_claude_lead_uses_json_format`/`test_cli_spec_lead_requires_mcp_format` green; the Step 3b-updated `test_spec_invariant`/`test_codex_is_lead_and_teammate`/`test_post_init_rejects_lead_without_filename` green; the S11b `teammate_launch_args` tests unaffected.

- [ ] **Step 5: Commit**

```bash
git add src/agent_team/cli_registry.py tests/unit/test_cli_registry.py
git commit -m "feat(s11c): D3/D4 codex lead-capable + CliSpec.mcp_format

Add mcp_format (json=file/--mcp-config, toml=CODEX_HOME profile/--profile);
lead now requires mcp_format (json also requires a filename). Flip codex
supports_lead=True, mcp_format='toml' (filename stays None — codex uses a
CODEX_HOME profile, not a session-dir file).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: D2 — format-dispatched `_write_lead_mcp_config` + codex profile renderer

**Files:**
- Modify: `src/agent_team/orchestrator.py`
- Test: `tests/unit/test_orchestrator.py`

- [ ] **Step 1: Write the failing tests**

In `tests/unit/test_orchestrator.py`, add (imports `sys`, `json`, `Path` are present; add `import tomllib` and `import os` at the top):

```python
def test_write_lead_mcp_config_codex_renders_codex_home_profile(
    tmp_path: Path, monkeypatch
) -> None:
    from agent_team.orchestrator import _write_lead_mcp_config

    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    project = tmp_path / "proj"
    project.mkdir()

    path = _write_lead_mcp_config(session_dir, "sid-1", project, cli="codex")

    # The profile lands in CODEX_HOME, named <profile>.config.toml — NOT in session_dir.
    assert path == codex_home / "agent-team-sid-1.config.toml"
    assert path.exists()
    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    server = parsed["mcp_servers"]["agent-team"]
    assert server["command"] == sys.executable
    assert server["args"] == ["-m", "agent_team.mcp_server"]
    assert server["env"]["AGENT_TEAM_SESSION_ID"] == "sid-1"
    assert server["env"]["AGENT_TEAM_PROJECT_PATH"] == str(project.resolve())


def test_write_lead_mcp_config_claude_still_writes_json(tmp_path: Path) -> None:
    from agent_team.orchestrator import _write_lead_mcp_config

    session_dir = tmp_path / "session"
    session_dir.mkdir()
    project = tmp_path / "proj"
    project.mkdir()

    path = _write_lead_mcp_config(session_dir, "sid-2", project, cli="claude")
    assert path == session_dir / "claude-mcp.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["mcpServers"]["agent-team"]["command"] == sys.executable
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/unit/test_orchestrator.py -k "write_lead_mcp_config_codex or write_lead_mcp_config_claude_still" -v`
Expected: FAIL — `_write_lead_mcp_config` only emits JSON today and uses `get_cli_spec(cli).mcp_config_filename` (None for codex → assertion/None path error).

- [ ] **Step 3: Add the codex helpers + bootstrap constant**

In `src/agent_team/orchestrator.py`, add `import os` to the imports block (after `import json`). Then, after the imports (before `def _check_lead_cli_supported`), add:

```python
# Bootstrap prompt for a codex lead (codex exec's PROMPT arg). One line, no double
# quotes (it is wrapped in "..." on the launch command line). The full lead
# context (D6 preamble + TEAM.md + playbook) is delivered via the working-root
# AGENTS.md, since codex has no --append-system-prompt-file.
_CODEX_LEAD_BOOTSTRAP = (
    "Read AGENTS.md in this working directory and orchestrate the team strictly "
    "per it, using ONLY the agent-team MCP tools. Do not read, edit, or run "
    "project code yourself."
)


def _codex_home() -> Path:
    """Codex's home dir (where profiles + auth live). Honors $CODEX_HOME."""
    env = os.environ.get("CODEX_HOME")
    return Path(env) if env else Path.home() / ".codex"


def _codex_profile_name(session_id: str) -> str:
    return f"agent-team-{session_id}"


def _lead_mcp_server_config(session_id: str, project_path: Path) -> dict:
    """The agent-team MCP server entry shared by every lead-config format.

    Runs under sys.executable (the interpreter with agent_team installed), not a
    bare 'python' that may differ in the pane. AGENT_TEAM_HOME captured at write
    time from default_base_dir().
    """
    return {
        "command": sys.executable,
        "args": ["-m", "agent_team.mcp_server"],
        "env": {
            "AGENT_TEAM_HOME": str(default_base_dir()),
            "AGENT_TEAM_SESSION_ID": session_id,
            "AGENT_TEAM_PROJECT_PATH": str(project_path.resolve()),
        },
    }


def _render_codex_profile_toml(server_cfg: dict) -> str:
    """Render the codex profile TOML for [mcp_servers.agent-team].

    json.dumps produces valid TOML for our values: a JSON string is a valid TOML
    basic string (backslashes doubled, so Windows paths survive: \\\\ -> \\), and a
    JSON list of strings is a valid TOML array. No lone backslashes are emitted,
    so there are no invalid TOML escapes.
    """
    lines = [
        "[mcp_servers.agent-team]",
        f"command = {json.dumps(server_cfg['command'])}",
        f"args = {json.dumps(server_cfg['args'])}",
        "",
        "[mcp_servers.agent-team.env]",
    ]
    for key, value in server_cfg["env"].items():
        lines.append(f"{key} = {json.dumps(value)}")
    return "\n".join(lines) + "\n"


def _write_codex_lead_agents_md(session_dir: Path, lead_context_text: str) -> Path:
    """Write the lead context to {session_dir}/lead/AGENTS.md; return the lead dir.

    codex exec -C <lead dir> uses this as its working root, so codex reads this
    AGENTS.md as the lead's system prompt (codex has no --append-system-prompt-file).
    Kept under session_dir (not the project) so the project's own AGENTS.md is not
    used and the project is not polluted.
    """
    lead_dir = session_dir / "lead"
    lead_dir.mkdir(parents=True, exist_ok=True)
    (lead_dir / "AGENTS.md").write_text(lead_context_text, encoding="utf-8")
    return lead_dir
```

- [ ] **Step 4: Format-dispatch `_write_lead_mcp_config`**

In `src/agent_team/orchestrator.py`, replace `_write_lead_mcp_config` (currently lines 40-74) with:

```python
def _write_lead_mcp_config(
    session_dir: Path, session_id: str, project_path: Path, *, cli: str
) -> Path:
    """Write the lead's MCP config in the CLI's format; return the written path.

    claude (json): {session_dir}/<registry filename>, loaded via --mcp-config.
    codex (toml): {CODEX_HOME}/agent-team-<sid>.config.toml, loaded via --profile
    (codex cannot load an arbitrary config-file path; a profile keeps only a
    shell-safe name on the launch line). --ignore-user-config isolates from the
    user's base config.toml while auth still resolves from CODEX_HOME.
    """
    spec = get_cli_spec(cli)
    server_cfg = _lead_mcp_server_config(session_id, project_path)
    if spec.mcp_format == "json":
        filename = spec.mcp_config_filename
        assert filename is not None  # json format guarantees a filename (CliSpec)
        config = {"mcpServers": {"agent-team": server_cfg}}
        path = session_dir / filename
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return path
    if spec.mcp_format == "toml":
        home = _codex_home()
        home.mkdir(parents=True, exist_ok=True)
        path = home / f"{_codex_profile_name(session_id)}.config.toml"
        path.write_text(_render_codex_profile_toml(server_cfg), encoding="utf-8")
        return path
    raise LeadCliNotSupportedError(
        f"Lead CLI {cli!r} has no MCP config renderer for format {spec.mcp_format!r}"
    )
```

- [ ] **Step 5: Run the targeted + existing orchestrator tests**

Run: `python -m pytest tests/unit/test_orchestrator.py -k "write_lead_mcp_config or renders_mcp_config_into_session_dir" -v`
Expected: PASS — new codex/claude renderer tests green; `test_start_renders_mcp_config_into_session_dir` (claude json path) still passes.

- [ ] **Step 6: Commit**

```bash
git add src/agent_team/orchestrator.py tests/unit/test_orchestrator.py
git commit -m "feat(s11c): D2 format-dispatched lead MCP config (codex TOML profile)

_write_lead_mcp_config now dispatches on CliSpec.mcp_format: claude writes the
JSON file as before; codex renders a CODEX_HOME profile
(agent-team-<sid>.config.toml) for --profile. Adds the shared server-config
builder + codex profile/AGENTS.md helpers + bootstrap prompt.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: D1/D3 — codex branch in `_build_lead_launch_command`

**Files:**
- Modify: `src/agent_team/orchestrator.py`
- Test: `tests/unit/test_orchestrator.py`

- [ ] **Step 1: Write the failing test**

In `tests/unit/test_orchestrator.py`, add:

```python
def test_build_lead_launch_command_for_codex_includes_required_tokens(
    tmp_path: Path,
) -> None:
    from agent_team.orchestrator import _build_lead_launch_command

    lead_dir = tmp_path / "session" / "lead"
    last = tmp_path / "session" / "lead-last.txt"
    line = _build_lead_launch_command(
        "codex",
        session_id="sid-9",
        project_path=tmp_path / "proj",
        lead_dir=lead_dir,
        output_last_message=last,
    )
    assert "codex" in line.split()[0].lower()
    assert "exec" in line
    assert "--ignore-user-config" in line
    assert "--skip-git-repo-check" in line
    # Profile NAME on the command line (shell-safe) — not inline -c values.
    assert "--profile agent-team-sid-9" in line
    assert f'-C "{lead_dir}"' in line
    assert f'-o "{last}"' in line
    # Bootstrap prompt is present and double-quote-wrapped.
    assert '"Read AGENTS.md' in line
    # NOT the claude flags.
    assert "--mcp-config" not in line
    assert "--append-system-prompt-file" not in line
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/unit/test_orchestrator.py::test_build_lead_launch_command_for_codex_includes_required_tokens -v`
Expected: FAIL — `_build_lead_launch_command` raises `LeadCliNotSupportedError` for codex (no arm yet) and its signature lacks the codex kwargs.

- [ ] **Step 3: Add the codex elif + widen the signature**

In `src/agent_team/orchestrator.py`, replace `_build_lead_launch_command` (currently lines 92-126) with:

```python
def _build_lead_launch_command(
    cli: str,
    *,
    mcp_config: Path | None = None,
    system_prompt_file: Path | None = None,
    session_id: str | None = None,
    project_path: Path | None = None,
    lead_dir: Path | None = None,
    output_last_message: Path | None = None,
) -> str:
    """Compose the lead CLI launch line send_keys'd to the lead pane (per-CLI).

    claude: --mcp-config <json> --strict-mcp-config --append-system-prompt-file.
    codex: codex exec --ignore-user-config --profile <name> -C <lead dir> -o ...
    + a bootstrap PROMPT (the lead context rides the working-root AGENTS.md, since
    codex has no --append-system-prompt-file). Stays an elif chain (no Protocol),
    per the S9 decision. Only registered lead CLIs reach here (start() gates via
    _check_lead_cli_supported).
    """
    if cli == "claude":
        # Full resolved exe (Windows: claude.CMD shim resolution is inconsistent
        # across PowerShell profiles); falls back to the bare name off PATH.
        exe = shutil.which(cli) or cli
        return (
            f'{exe} --mcp-config "{mcp_config}" --strict-mcp-config '
            f'--append-system-prompt-file "{system_prompt_file}"'
        )
    if cli == "codex":
        exe = shutil.which(cli) or cli
        profile = _codex_profile_name(session_id)
        return " ".join(
            [
                exe,
                "exec",
                "--ignore-user-config",
                "--skip-git-repo-check",
                "--profile",
                profile,
                "-C",
                f'"{lead_dir}"',
                "-o",
                f'"{output_last_message}"',
                f'"{_CODEX_LEAD_BOOTSTRAP}"',
            ]
        )
    # Defensive: a registered lead CLI without an arm is a registry/builder
    # mismatch. antigravity/gemini land here until S12 adds their arm.
    raise LeadCliNotSupportedError(
        f"Lead CLI {cli!r} is registered but has no launch builder "
        f"(antigravity/gemini planned for S12+)"
    )
```

- [ ] **Step 4: Run the targeted test**

Run: `python -m pytest tests/unit/test_orchestrator.py::test_build_lead_launch_command_for_codex_includes_required_tokens tests/unit/test_orchestrator.py::test_build_lead_launch_command_for_claude_includes_required_tokens -v`
Expected: PASS — codex line built; the claude test still passes (claude branch + signature unchanged; new params are optional).

- [ ] **Step 5: Commit**

```bash
git add src/agent_team/orchestrator.py tests/unit/test_orchestrator.py
git commit -m "feat(s11c): D1/D3 codex elif in _build_lead_launch_command

codex lead launch: codex exec --ignore-user-config --skip-git-repo-check
--profile agent-team-<sid> -C <lead dir> -o <last> '<bootstrap>'. Only
shell-safe tokens on the line (profile name + double-quoted paths/prompt).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: D4 — format-aware `start()` wiring + update the 2 codex-refusal tests

**Files:**
- Modify: `src/agent_team/orchestrator.py` (`start()`)
- Test: `tests/unit/test_orchestrator.py`

- [ ] **Step 1: Update the two now-wrong existing tests + add a codex start test**

In `tests/unit/test_orchestrator.py`:

(a) `test_unsupported_lead_cli_raises_registry_error` (currently parametrized `["codex", "antigravity", "xyz"]`): remove `"codex"` (it now has a launch arm). Change the parametrize to `["antigravity", "xyz"]` and update the docstring line to say antigravity/unknown reach the defensive arm. Also update its `match=` if needed: the defensive message now says "S12+", so change `match="S11"` to `match="S12"`.

(b) `test_start_refuses_unsupported_lead_cli_before_touching_disk` (currently parametrized `["codex", "antigravity", "xyz"]`): remove `"codex"` → `["antigravity", "xyz"]` (codex is now an accepted lead).

(c) Add a codex-lead start test (uses the `no_psmux=False` start with mock psmux; redirect CODEX_HOME to tmp). Place it near the other start tests; reuse the `_start_with_minimal` helper but with `lead_cli` set via the project config. Since `lead_cli` comes from `config.yaml`, write it into the minimal project's config before start:

```python
def test_start_codex_lead_writes_profile_agents_and_sends_codex_exec(
    minimal_project: Path,
    session_store: SessionStore,
    psmux_backend: PsmuxBackend,
    persona_registry: PersonaRegistry,
    event_log: EventLog,
    tmp_path: Path,
    monkeypatch,
) -> None:
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    # Flip the lead to codex via config (D4: config-driven lead selection).
    config_path = minimal_project / ".agent-team" / "config.yaml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + "\nlead_cli: codex\n",
        encoding="utf-8",
    )

    orch, ctx = _start_with_minimal(
        minimal_project,
        session_id="s11c-codex",
        session_store=session_store,
        psmux_backend=psmux_backend,
        persona_registry=persona_registry,
        event_log=event_log,
    )
    try:
        orch.start(project_path=minimal_project)
    finally:
        orch.stop_watching()

    # Profile written to CODEX_HOME.
    profile = codex_home / "agent-team-s11c-codex.config.toml"
    assert profile.exists()
    # Lead context delivered via working-root AGENTS.md (D6 preamble inside).
    agents_md = ctx.session_dir / "lead" / "AGENTS.md"
    assert agents_md.exists()
    assert "You are the team LEAD" in agents_md.read_text(encoding="utf-8")
    # Lead pane launched with codex exec + profile.
    send_calls = [c for c in psmux_backend.recorded_calls if "send-keys" in c.args]
    payload = " ".join(send_calls[0].args)
    assert "codex" in payload
    assert "exec" in payload
    assert "--profile agent-team-s11c-codex" in payload
    assert "--mcp-config" not in payload  # not the claude path
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/unit/test_orchestrator.py -k "codex_lead_writes_profile or refuses_unsupported or unsupported_lead_cli_raises" -v`
Expected: FAIL — `start()` still uses the claude-only launch wiring (no codex branch), so the codex profile/AGENTS.md are not written and the send payload lacks `codex exec`. (The two edited parametrized tests now also fail on the removed-codex expectation until `start()`/builder accept codex.)

- [ ] **Step 3: Make `start()` launch format-aware**

In `src/agent_team/orchestrator.py`, in `start()`, replace the launch block inside `if not self.ctx.no_psmux:` (currently lines 227-240, from `mcp_config_path = _write_lead_mcp_config(...)` through the `launch_cmd = _build_lead_launch_command(...)` assignment) with:

```python
                spec = get_cli_spec(lead_cli)
                mcp_config_path = _write_lead_mcp_config(
                    self.ctx.session_dir, self.ctx.session_id, project_path, cli=lead_cli
                )
                lead_context = loader.build_lead_context(
                    playbook_name=playbook, extra_context=context_text
                )
                if spec.mcp_format == "json":
                    prompt_path = _write_lead_system_prompt(
                        self.ctx.session_dir, lead_context.text
                    )
                    launch_cmd = _build_lead_launch_command(
                        lead_cli,
                        mcp_config=mcp_config_path,
                        system_prompt_file=prompt_path,
                    )
                else:  # toml (codex): working-root AGENTS.md + --profile
                    lead_dir = _write_codex_lead_agents_md(
                        self.ctx.session_dir, lead_context.text
                    )
                    launch_cmd = _build_lead_launch_command(
                        lead_cli,
                        session_id=self.ctx.session_id,
                        project_path=project_path,
                        lead_dir=lead_dir,
                        output_last_message=self.ctx.session_dir / "lead-last.txt",
                    )
```

(The lines that follow — `new_session(... cwd=project_path)`, `send_keys(lead_pane, launch_cmd)`, the TUI `split_pane`, member update — stay unchanged.)

- [ ] **Step 4: Clean up the codex profile on partial-start failure**

The codex profile lives in CODEX_HOME (outside `session_dir`), so the existing `shutil.rmtree(session_dir)` in the `except` block does not remove it. In `start()`'s `except Exception:` block (currently lines 270-291), after the `shutil.rmtree(self.ctx.session_dir)` try/except, add:

```python
            # The codex lead profile lives in CODEX_HOME, outside session_dir, so
            # the rmtree above misses it. Best-effort remove on partial start.
            try:
                profile = (
                    _codex_home()
                    / f"{_codex_profile_name(self.ctx.session_id)}.config.toml"
                )
                profile.unlink(missing_ok=True)
            except OSError as profile_exc:
                print(
                    "Orchestrator.start codex profile cleanup failed: "
                    f"{profile_exc!r}",
                    file=sys.stderr,
                )
```

> NOTE: graceful end-of-session profile cleanup pairs with the carried-backlog `Orchestrator.shutdown` item (out of S11c scope); this only covers the partial-start path. Document the leftover-profile note in `tests/manual` (Task 5).

- [ ] **Step 5: Run the orchestrator suite**

Run: `python -m pytest tests/unit/test_orchestrator.py -v`
Expected: PASS — the codex start test, the two edited parametrized tests, and all existing claude start tests green.

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest tests/ -q`
Expected: PASS. Check `tests/unit/test_payment_api_fixture.py` and `tests/unit/test_cli_start_attach.py` (they reference lead_cli/mcp) — they should be unaffected (default lead_cli is claude); if one asserted "codex is not lead-supported", update it to the new truth.

- [ ] **Step 7: Commit**

```bash
git add src/agent_team/orchestrator.py tests/unit/test_orchestrator.py
git commit -m "feat(s11c): D4 config-driven codex lead launch wiring

start() now branches on CliSpec.mcp_format: claude keeps the JSON+system-prompt
path; codex writes the working-root lead AGENTS.md and launches codex exec with
the CODEX_HOME profile. Partial-start cleanup also removes the codex profile.
Update the two now-stale 'codex unsupported as lead' tests.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Manual checklist + docs + verify

**Files:**
- New: `tests/manual/s11c-codex-lead.md`
- Modify: `PROGRESS.md`, `docs/s11-multi-cli-plan.md`

- [ ] **Step 1: Write the live-verification checklist**

Create `tests/manual/s11c-codex-lead.md` (style of `tests/manual/s9-claude-lead.md`). Cover the live behaviors unit tests cannot:

```markdown
# S11c manual checklist — codex as lead (D1–D4)

Run on the Windows box with real codex (0.139.0) + psmux. Unit tests cover the
launch-line/profile construction; these confirm codex actually leads.

## Setup
- [ ] Check `{CODEX_HOME}/` has no pre-existing `agent-team-*.config.toml` profile
      that could collide (low risk — sid-scoped, agent-team is new).
- [ ] In a fixture project's `.agent-team/config.yaml`, set `lead_cli: codex`.
- [ ] `agent-team start --session s11c --project <fixture>`.

## Profile + isolation (the load-bearing live unknown)
- [ ] Confirm `{CODEX_HOME}/agent-team-s11c.config.toml` was written with
      `[mcp_servers.agent-team]`.
- [ ] Confirm `codex exec --ignore-user-config --profile agent-team-s11c` actually
      LOADS the profile's MCP server (i.e. --ignore-user-config does not also block
      the profile). If it does block it, note here and fall back (e.g. drop
      --ignore-user-config, or use inline -c): ____________________

## Lead behaves
- [ ] The codex lead pane launches (no shell-quoting breakage of the command line).
- [ ] codex connects to the agent-team MCP server and can call a tool
      (e.g. list_personas / spawn_teammate round-trip).
- [ ] codex reads `{session_dir}/lead/AGENTS.md` (the D6 preamble) and orchestrates
      per it — delegates coding, does not edit project files itself.
- [ ] Autonomous mode: codex exec drives spawn/mail/wait via MCP and exits when
      done; user approvals go through the TUI queue.

## Cleanup
- [ ] After the session, `{CODEX_HOME}/agent-team-s11c.config.toml` is leftover
      (graceful cleanup is the carried-backlog Orchestrator.shutdown item). Remove
      it manually for now if desired.

## Cost dial
- [ ] Flip `lead_cli` back to `claude` → next start launches the claude lead with
      no code change (revert = one-line config).
```

- [ ] **Step 2: Note the D2 profile deviation in the spec touch-points**

In `docs/s11-multi-cli-plan.md`, update the codex touch-points/D2 references so they say codex uses a **CODEX_HOME `--profile`** (`agent-team-<sid>.config.toml`), not a session-dir `codex-mcp.toml`, and `mcp_config_filename` stays `None` for codex (codex cannot load an arbitrary config-file path). Keep it a short note; do not rewrite the decision tables.

- [ ] **Step 3: Add the S11c entry to PROGRESS.md**

In `PROGRESS.md`, add an S11c "done" entry: D1 (per-CLI launch dispatch + codex arm), D2 (format-dispatched MCP config; codex CODEX_HOME profile), D3 (codex `supports_lead`+`mcp_format`), D4 (config-driven `lead_cli`); note the live codex-lead E2E is the `tests/manual/s11c-codex-lead.md` checklist. Match the existing style.

- [ ] **Step 4: Full verification**

Run: `python -m pytest tests/ -q`
Expected: PASS — S11b's 237 + S11c additions (registry ×4, write-config ×2, launch-line ×1, start ×1 = +8), minus the 2 removed codex parametrize cases (net +~6/+8 depending on parametrization counting).

Run: `python -m ruff check src/ tests/`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add tests/manual/s11c-codex-lead.md PROGRESS.md docs/s11-multi-cli-plan.md
git commit -m "docs(s11c): manual codex-lead checklist + PROGRESS + profile-deviation note

Live codex-as-lead verification checklist (profile load under --ignore-user-config
is the key live unknown), S11c PROGRESS entry, and the D2 note that codex uses a
CODEX_HOME --profile rather than a session-dir codex-mcp.toml.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage (docs/s11-multi-cli-plan.md):**
- **D1** (per-CLI launch dispatch, elif chain, codex arm) → Task 3. ✓
- **D2** (format-dispatched MCP config renderer; `mcp_format`) → Task 1 (field) + Task 2 (dispatch). Codex uses a CODEX_HOME profile (documented deviation from "session-dir codex-mcp.toml", with rationale: codex can't load an arbitrary file path). ✓
- **D3** (codex 2nd lead: `--ignore-user-config`, MCP injected, system prompt via PROMPT + AGENTS.md) → Tasks 1–4. Uses `--profile` (per D2/D3 "or a rendered codex-mcp.toml profile via --profile"). ✓
- **D4** (config-driven `lead_cli`) → already read in `start()`; Task 4 makes codex a working value + the codex-config start test. ✓
- Touch-points (`cli_registry.py`, `orchestrator.py` two seams, tests) → covered. Live E2E → Task 5 manual checklist (per policy). ✓

**2. Placeholder scan:** No TBD/TODO; complete code in every code step. Task 4 Step 1 (a)/(b) are precise edits to named existing tests; Task 5 artifacts are prose-by-design. ✓

**3. Type consistency:**
- `CliSpec.mcp_format: str | None` (Task 1) read in `_write_lead_mcp_config` + `start()` (Tasks 2/4). Invariant updated to match. ✓
- `_lead_mcp_server_config(session_id, project_path) -> dict` (Task 2) used by `_write_lead_mcp_config` (json + toml). `_render_codex_profile_toml(server_cfg)`, `_codex_home()`, `_codex_profile_name(session_id)`, `_write_codex_lead_agents_md(session_dir, text) -> Path`, `_CODEX_LEAD_BOOTSTRAP` (Task 2) used in Tasks 3/4. ✓
- `_build_lead_launch_command` widened signature (Task 3): claude uses `mcp_config`/`system_prompt_file`; codex uses `session_id`/`project_path`(unused in line but kept for parity)/`lead_dir`/`output_last_message`. Both call sites in `start()` (Task 4) match. ✓
  - NOTE: `project_path` is passed to the codex builder for signature parity but the codex line does not embed it (project path reaches the MCP server via the profile env, written in Task 2). Acceptable; or drop it from the codex call — keep for symmetry with the claude env.

**4. Existing-test impact (explicit):** `test_unsupported_lead_cli_raises_registry_error` and `test_start_refuses_unsupported_lead_cli_before_touching_disk` both drop `"codex"` (Task 4 Step 1). The claude launch/render tests are unaffected (claude branch + JSON path unchanged). Defensive-arm message changes S11→S12.

## Expert review axes

Plan-review (BLOCKING=0) and code-review (BLOCKING+P1) candidate axes:
- **E1 Registry/CliSpec** — `mcp_format` field, invariant change, frozen-dataclass default ordering, codex flip; no teammate-path regression.
- **E2 MCP config render** — codex TOML profile validity (parses via tomllib), Windows-path escaping in TOML (json.dumps → valid TOML basic string), CODEX_HOME resolution, claude JSON unchanged.
- **E3 Launch line** — codex `codex exec` line correctness, shell-safety (only profile name + double-quoted paths/prompt; no fragile inline values), `--ignore-user-config`+`--profile` semantics (flag as the key live unknown), elif-chain + defensive arm.
- **E4 start() wiring + tests** — format branch correctness, lead AGENTS.md delivery, partial-start profile cleanup, the 2 edited tests, codex-config start test, no claude regression.
- **E5 Isolation/decoupling + observability** — lead-only change (teammate invariant intact), CODEX_HOME profile isolation + auth, leftover-profile cleanup scope, autonomous-lead property documented.
