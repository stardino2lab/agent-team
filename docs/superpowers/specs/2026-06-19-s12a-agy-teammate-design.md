# S12a — agy (Antigravity) teammate — design

Date: 2026-06-19
Status: approved (brainstorm), pending implementation plan

## Context

S12's earlier S12a slice registered **gemini** as a teammate-only CLI (registry
entry + `gemini-implementer`/`gemini-planner` personas + 6 unit tests, code-complete
at 248 passed). The user has redirected: develop against the **agy** (Antigravity)
CLI instead of gemini. This spec **completely replaces** the gemini S12a work with
agy — the gemini registry entry, personas, and tests are removed, not kept alongside.

`agy` is the Antigravity CLI (v1.0.10, `C:\Users\stard\AppData\Local\agy\bin\agy.exe`),
a Claude-Code-derived agent CLI. Its flag surface mirrors Claude Code:
`--add-dir`, `--continue`/`-c`, `--dangerously-skip-permissions`, `-p`/`--print`,
`--prompt`/`--prompt-interactive`/`-i`, `--model`, `--sandbox`, plus `plugin`,
`models`, `install`, `update` subcommands.

Notably **absent**: any `mcp` subcommand, `--mcp-config`, `--strict-mcp-config`, or
`--append-system-prompt` flag (`agy help mcp` → "unknown subcommand: mcp"). MCP, if
supported at all, would come via the Claude-Code `.mcp.json` project convention or
the `plugin` system — unverified. This is why agy is **teammate-only** here; lead
(which requires the MCP server handshake) is deferred to a separate spike.

## Scope

In: replace the gemini S12a teammate slice with agy.
Out (deferred): agy as lead, MCP wiring, `.mcp.json` auto-detection spike, `--sandbox`.

## Naming (two distinct identifiers)

- **cli / registry name = `agy`** — locked. The persona `cli:` value is used three
  ways with the same string: registry lookup key (`get_cli_spec`/`is_teammate_supported`),
  the literal launch command (`" ".join([p.cli, *launch_args])` → `agy …`), and
  lead-support / spawn-approval validation. The binary is `agy`, so this must be `agy`.
- **persona name = `agy-implementer` / `agy-planner`** — a free label (persona dict
  key, `allowed_personas` config entry, `spawn_teammate(persona=…)` argument). Follows
  the existing `<cli>-<role>` convention (mirrors `gemini-implementer`).

## Design

### 1. Registry (`cli_registry.py`)

Remove the `gemini` `CliSpec`. Add `agy`:

```python
"agy": CliSpec(
    name="agy",
    supports_lead=False,        # lead deferred: no MCP subcommand (separate spike)
    supports_teammate=True,
    mcp_config_filename=None,
    teammate_launch_args=("--dangerously-skip-permissions",),
    mcp_format=None,
),
```

`--dangerously-skip-permissions` is confirmed present in `agy --help`
("Auto-approve all tool permission requests without prompting") — the single
Claude-Code-style auto-approve flag (replaces gemini's `--approval-mode yolo
--skip-trust` pair). The teammate runs **interactively** in its pane and receives
the send_keys kickoff, so this is an interactive auto-approve flag, NOT headless
`-p`/`--print` (which would single-shot and exit before the kickoff). `--sandbox`
is opt-in and omitted — a teammate needs full workspace access.

Update the module docstring (the gemini line and the "antigravity not registered"
note) to reflect agy as a registered teammate-only CLI.

### 2. Personas

Remove `gemini-implementer.yaml` / `gemini-planner.yaml` from both `bundled/personas/`
and the root `personas/` mirror. Add `agy-implementer.yaml` / `agy-planner.yaml`
(byte-for-byte mirrored across both trees for the parity invariant), `cli: agy`,
content mirroring the gemini personas (heavy coding + planning, unlimited quota).

Opt-in: no default/fixture/template `allowed_personas` includes them — existing
claude/codex teams are unaffected.

### 3. Unit tests

Replace the 6 gemini cases with agy equivalents (no count change — target stays
248 passed). Assertions are never weakened:

- registry: agy spec lookup + `supports_lead=False`/`supports_teammate=True`
- persona load: `agy-implementer` loads with `cli: agy`
- spawn: the teammate launch command contains `--dangerously-skip-permissions`
  (substring assertion)
- bundled importlib + parity set extended to the agy personas, gemini dropped
- `test_spawn_passes_persona_cli_to_split_pane` parametrize: gemini case → agy

### 4. Live gate doc

Replace `tests/manual/s12-gemini-gates.md` with `tests/manual/s12-agy-gates.md`:

- **G0 (no token, already verified):** `agy --version` → exit 0;
  `--dangerously-skip-permissions`, `-p/--print`, `--prompt-interactive` present in
  `agy --help`. ✅ confirmed on this box (agy 1.0.10).
- **G1 (token):** an interactive `agy --dangerously-skip-permissions` pane accepts a
  psmux send_keys kickoff and runs tool calls with no per-command approval and no
  trust prompt.
- **Helper-under-agy (token):** the `agent-team` shell helper (mail / task /
  `teammate ready`) runs under agy on Windows.
- **Lead gates (deferred):** the MCP-dependent gates are out of scope until the
  `.mcp.json` / plugin MCP spike resolves whether agy can host our server.

### 5. Progress / implementation docs

Update `PROGRESS.md` (+ `PROGRESS.ko.md`) and `docs/IMPLEMENTATION.md` / the S12
plan docs: retarget the S12 milestone and the S12a slice from gemini to agy. Note
the gemini work was superseded (the commits remain in history; the files are
removed going forward).

## Testing

Unit: 248 passed maintained (gemini cases swapped for agy), ruff clean. Live agy
behavior (interactive launch, auto-approve, trust prompt, the shell helper under
agy) is NOT auto-tested — it needs the real binary + tokens + auth, captured in
`tests/manual/s12-agy-gates.md`.

## Risks / open questions

- **Trust prompt:** Claude-Code-derived CLIs can show a first-run "trust this
  folder" prompt. `--dangerously-skip-permissions` is expected to bypass it (it does
  in Claude Code), but this is a G1 live-verification item, not a code assumption.
- **Lead viability:** unknown until the MCP spike — explicitly out of scope here.
