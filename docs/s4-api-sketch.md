# S4 API Sketch — PsmuxBackend

Review input for 5-expert gate. Implementation follows after BLOCKING=0.

## Design decisions

| Item | Decision |
|------|----------|
| Executable | `psmux` only (NFR-01); resolve once via `shutil.which` at init |
| Subprocess | `shell=False` always; argv `list[str]` only — no `os.system`, no string join |
| Mock mode | `PsmuxBackend(mock=True)` records argv, tracks pane state, no subprocess |
| Session names | `safe_segment(name, "psmux_session")` on `new_session`, `split_pane`, `list_panes` |
| Pane targets | `%N` validated `^%[0-9]+$` pass-through; else treat as session name → `safe_segment` |
| Session field | API param `session` / `name` = `Session.psmux_session` (may differ from `session_id`) |
| pane_id (mock) | Monotonic `%0`, `%1`, …; `kill_pane` removes from mock state |
| pane_id (real) | `list-panes -F "#{pane_id}"` diff after split/create |
| Errors | `PsmuxNotFoundError`, `PsmuxCommandError` (`command_args`, `args` alias, `exit_code`, `stderr`); reuse `InvalidPathSegmentError` |
| cwd | Optional `cwd: Path | None` → single `-c` argv token (resolved path string) |
| command | After `--`, append **one** argv element (full shell line); never `shlex.split(command)` |
| send_keys | `[executable, "send-keys", "-t", target, "-l", keys]` + `["Enter"]` if `enter` |
| recorded_calls | Mock only; returns `list(RecordedCall)` copy; real mode → empty list |
| S8 downstream | Orchestrator injects backend; persists returned `pane_id` → `Member.pane_id`, `backend="psmux"` |

## psmux command mapping

| Method | psmux argv (after executable) |
|--------|--------------------------------|
| `new_session` | `new-session -d -s NAME [-c cwd] [-- CMD]` |
| `split_pane` | `split-window -t NAME -d -h\|-v [-p PCT] [-c cwd] [-- CMD]` |
| send_keys | `send-keys -t TARGET -l KEYS [Enter]` |
| `kill_pane` | `kill-pane -t TARGET` |
| `list_panes` | `list-panes -t NAME -F "#{pane_id}"` |

`-d` on split: always passed — new pane without stealing focus.

## `psmux_backend.py`

### Types

```python
@dataclass
class PaneInfo:
    pane_id: str

@dataclass
class RecordedCall:
    args: list[str]
    cwd: str | None = None

class PsmuxNotFoundError(FileNotFoundError): ...

class PsmuxCommandError(RuntimeError):
    exit_code: int
    command_args: list[str]
    stderr: str  # truncated e.g. 500 chars; .args aliases command_args
```

Import `InvalidPathSegmentError`, `safe_segment` from `agent_team._io`.

### PsmuxBackend

```python
class PsmuxBackend:
    def __init__(self, *, executable: str = "psmux", mock: bool = False) -> None

    @property
    def recorded_calls(self) -> list[RecordedCall]:
        # mock: copy of internal list; non-mock: []

    def new_session(self, name: str, *, command: str | None = None, cwd: Path | None = None) -> str

    def split_pane(
        self,
        session: str,
        *,
        direction: Literal["horizontal", "vertical"] = "horizontal",
        command: str | None = None,
        cwd: Path | None = None,
        size_percent: int | None = None,  # optional validate 1..100
    ) -> str

    def send_keys(self, target: str, keys: str, *, enter: bool = True) -> None

    def kill_pane(self, target: str) -> None

    def list_panes(self, session: str) -> list[PaneInfo]
```

### Internal helpers

```python
def _validate_session_name(self, name: str) -> str:
    return safe_segment(name, "psmux_session")

def _validate_target(self, target: str) -> str:
    if target.startswith("%"):
        if not re.fullmatch(r"%[0-9]+", target):
            raise InvalidPathSegmentError(f"Invalid pane target: {target!r}")
        return target
    return safe_segment(target, "psmux_session")

def _build_argv(self, *parts: str, command: str | None = None) -> list[str]:
    argv = list(parts)
    if command is not None:
        argv.extend(["--", command])  # single argv element after --
    return argv

def _run(self, args: list[str], *, cwd: Path | None = None) -> str:
    # mock: RecordedCall + return stdout ""
    # real: subprocess.run([executable, *args], shell=False, capture_output=True, text=True)
    #   → PsmuxNotFoundError if which failed at init
    #   → PsmuxCommandError(exit_code, args, stderr) on non-zero
```

### Real-mode pane_id

**split:** before/after `list_panes` set diff → new id or `PsmuxCommandError`.

**new_session:** `list_panes(name)` after create; zero panes → `PsmuxCommandError`.

### Mock state

- Track `set[str]` pane ids per session name.
- `new_session` → add `%0`; `split_pane` → add next id; `kill_pane` → discard target id.
- `list_panes` → sorted tracked ids for session.

## Error handling

| Case | Exception |
|------|-----------|
| `psmux` not in PATH (non-mock) | `PsmuxNotFoundError` |
| Non-zero exit | `PsmuxCommandError` |
| Bad session name | `InvalidPathSegmentError` |
| Bad `%N` target | `InvalidPathSegmentError` |
| Split/create produced no pane | `PsmuxCommandError` |

## Test matrix (7+)

| Test | Scenario |
|------|----------|
| mock new_session | argv + `%0`; optional `command`/`cwd` in RecordedCall |
| mock split_pane | `%1`, `%2`; `-d -h`; vertical + size_percent optional |
| mock send_keys | `send-keys -t %0 hello Enter`; `enter=False` omits Enter |
| mock kill_pane | argv + pane removed from `list_panes` |
| mock list_panes | tracks mock state |
| missing executable | `mock=False`, patch `which` → `PsmuxNotFoundError` |
| safe_segment reject | `new_session("../evil")` |
| target validation | `kill_pane("%bad")` → `InvalidPathSegmentError` |
| PsmuxCommandError | mock `subprocess.run` returncode≠0 |

Fixture: function-scoped `PsmuxBackend(mock=True)` per test (no shared recorded_calls).

Optional integration (not in S4 min):

```python
@pytest.mark.integration
@pytest.mark.skipif(shutil.which("psmux") is None, reason="psmux not installed")
def test_real_new_session_and_list(): ...
```

Register `integration` marker in `pyproject.toml`.

## Files (post-gate)

| File | Role |
|------|------|
| `src/agent_team/psmux_backend.py` | Backend wrapper |
| `tests/unit/test_psmux_backend.py` | 7+ unit tests |
| `tests/conftest.py` | optional function-scoped fixture |
| `pyproject.toml` | `integration` pytest marker |
| `PROGRESS.md` | after implement + code gate |

## Out of scope (S4)

- `agent-team start` / orchestrator (S8)
- attach/detach CLI (S9)
- TUI (S7)
- `SessionStore` / `Member` writes

## Downstream (S8)

```python
backend = PsmuxBackend(mock=dry_run)  # --no-psmux: skip backend, pane_id=None
lead_id = backend.new_session(
    psmux_session, command=lead_cmd, cwd=project_path,
)
backend.split_pane(psmux_session, direction="horizontal", command=tui_cmd, cwd=project_path)
# TUI pane not stored in members[]
teammate_id = backend.split_pane(psmux_session, command=spawn_cmd, cwd=project_path)
# orchestrator: Member(..., pane_id=teammate_id, backend="psmux")
```

`shutdown_teammate`: if `member.pane_id` → `kill_pane(member.pane_id)`; emit event; update session.json.
