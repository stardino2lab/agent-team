# S5 API Sketch — Spawn Approval

Review input for 5-expert gate. Implementation follows after BLOCKING=0.

## Design decisions

| Item | Decision |
|------|----------|
| Storage | `{session_dir}/approval/pending.json` (single active request) + `resolutions.jsonl` append-only |
| request_id | `apr-{NNN}` auto-increment via scan of pending + resolutions lines |
| Full prompt | `prompt` stored in pending; `prompt_preview` = first 200 chars for TUI |
| Single pending | Second `request_spawn` while pending exists → `SpawnPendingError` |
| Persona/cli | Caller supplies `cli`; S5 does **not** verify persona exists or cli matches registry (S6/S8 enforce via `PersonaRegistry`) |
| Teammate name | Optional `teammate_name` on request; orchestrator generates if omitted (S8) |
| Mutations + audit | Optional `event_log=EventLog()` on request / approve / deny |
| Resolution | Approve/deny append resolution line, **delete** `pending.json` |
| decided_by | Default `"user"` (TUI); tests may pass `"test"` |

## pending.json schema

```json
{
  "request_id": "apr-001",
  "persona": "implementer",
  "cli": "codex",
  "prompt": "Implement payment endpoint per task board...",
  "prompt_preview": "Implement payment endpoint per task board...",
  "teammate_name": "implementer-1",
  "requested_by": "lead",
  "requested_at": "2026-06-10T12:05:00Z",
  "status": "pending"
}
```

`teammate_name` omitted → JSON `null`.

## resolution line (resolutions.jsonl)

**Denied** (minimal):

```json
{
  "request_id": "apr-001",
  "decision": "denied",
  "decided_at": "2026-06-10T12:05:10Z",
  "decided_by": "user"
}
```

**Approved** (includes spawn snapshot for S8 file-based handoff):

```json
{
  "request_id": "apr-001",
  "decision": "approved",
  "decided_at": "2026-06-10T12:05:10Z",
  "decided_by": "user",
  "persona": "implementer",
  "cli": "codex",
  "prompt": "Implement payment endpoint per task board...",
  "teammate_name": "implementer-1",
  "requested_by": "lead"
}
```

`teammate_name` may be JSON `null`. Orchestrator reads **latest approved** resolution with matching `request_id` to spawn; no in-memory cache required.

## Event payloads (EventLog)

| Event | When | Payload |
|-------|------|---------|
| `spawn_requested` | `request_spawn` | `request_id`, `persona`, `cli`, `requested_by` |
| `spawn_approved` | `approve` | `request_id`, `persona` |
| `spawn_denied` | `deny` | `request_id` |

Matches IMPLEMENTATION §event line + s1-api-sketch. `spawn_requested` adds `request_id` (intentional; audit correlation).

## `spawn_approval.py`

### Types

```python
@dataclass
class SpawnRequest:
    request_id: str
    persona: str
    cli: str
    prompt: str
    prompt_preview: str
    teammate_name: str | None
    requested_by: str
    requested_at: str
    status: Literal["pending"]

@dataclass
class SpawnResolution:
    request_id: str
    decision: Literal["approved", "denied"]
    decided_at: str
    decided_by: str
    persona: str | None = None
    cli: str | None = None
    prompt: str | None = None
    teammate_name: str | None = None
    requested_by: str | None = None

class SpawnPendingError(RuntimeError): ...
class SpawnRequestNotFoundError(LookupError): ...
class SpawnRequestMismatchError(ValueError): ...  # approve/deny wrong request_id
```

### SpawnApproval

```python
_PREVIEW_LEN = 200

class SpawnApproval:
    def request_spawn(
        self,
        session_dir: Path,
        *,
        persona: str,
        cli: str,
        prompt: str,
        requested_by: str,
        teammate_name: str | None = None,
        event_log: EventLog | None = None,
    ) -> SpawnRequest

    def get_pending(self, session_dir: Path) -> SpawnRequest | None

    def approve(
        self,
        session_dir: Path,
        request_id: str,
        *,
        decided_by: str = "user",
        event_log: EventLog | None = None,
    ) -> SpawnResolution

    def deny(
        self,
        session_dir: Path,
        request_id: str,
        *,
        decided_by: str = "user",
        event_log: EventLog | None = None,
    ) -> SpawnResolution

    def read_resolutions(self, session_dir: Path) -> list[SpawnResolution]
```

### Helpers

```python
def _pending_path(session_dir: Path) -> Path
def _resolutions_path(session_dir: Path) -> Path
def _next_request_id(session_dir: Path) -> str
def _make_preview(prompt: str, n: int = _PREVIEW_LEN) -> str
def _write_pending(session_dir: Path, request: SpawnRequest) -> None  # write_json; mkdir approval/
def _clear_pending(session_dir: Path) -> None
def _append_resolution(session_dir: Path, resolution: SpawnResolution) -> None  # append JSONL line
```

Use `agent_team._io`: `write_json`, `read_json`, `format_ts`, `utc_now`.

**`approve` order:** read pending → validate `request_id` → build resolution (copy spawn fields) → append resolution → emit `spawn_approved` → delete pending.

**`deny` order:** read pending → validate → append minimal resolution → emit `spawn_denied` → delete pending.

Validation:
- `safe_segment(persona, "persona")`
- `safe_segment(requested_by, "requester")`
- `cli in ("claude", "codex")`
- if `teammate_name`: `safe_segment(teammate_name, "teammate")`

## Error handling

| Case | Exception |
|------|-----------|
| pending.json already exists | `SpawnPendingError` |
| approve/deny, no pending | `SpawnRequestNotFoundError` |
| approve/deny, request_id mismatch | `SpawnRequestMismatchError` |
| Invalid persona/requester/teammate segment | `InvalidPathSegmentError` |
| Invalid cli | `ValueError` |

## Test matrix (10+)

| Test | Scenario |
|------|----------|
| request_spawn | pending written; `spawn_requested` payload asserted |
| get_pending | returns request; after approve → `None` |
| second request | `SpawnPendingError` |
| approve | approved resolution has spawn snapshot; pending removed; `spawn_approved` event |
| deny | minimal resolution; pending removed; `spawn_denied` event |
| request_id mismatch | `SpawnRequestMismatchError` on approve and deny |
| no pending | `SpawnRequestNotFoundError` on approve |
| read_resolutions | multiple lines; approved row has persona/cli/prompt |
| next_request_id | apr-001 → apr-002 |
| safe_segment reject | bad persona → `InvalidPathSegmentError` |
| invalid cli | `ValueError` |
| prompt_preview | long prompt truncated to 200 chars |
| without event_log | no `events.jsonl` on request |

Fixtures: `session_dir` from conftest; `event_log` fixture.

## Files (post-gate)

| File | Role |
|------|------|
| `src/agent_team/spawn_approval.py` | approval queue |
| `tests/unit/test_spawn_approval.py` | 6+ tests |
| `PROGRESS.md` | S5 done after implement + code gate |

## Out of scope (S5)

- TUI modal (S7)
- MCP `spawn_teammate` tool (S6)
- Orchestrator spawn after approve (S8)
- `allowed_personas` enforcement (S6/S8 calls `PersonaRegistry.is_allowed` before request)
- Writing `teammates/{name}/spawn-prompt.txt` (S8)

## Downstream (S6/S7/S8)

```python
# S6 MCP spawn_teammate — map MCP name? → teammate_name
persona_obj = registry.get(persona)
req = approval.request_spawn(
    session_dir,
    persona=persona,
    cli=persona_obj.cli,
    prompt=prompt,
    requested_by="lead",
    teammate_name=name,
    event_log=log,
)
return {"request_id": req.request_id, "status": "pending"}

# S7 TUI
pending = approval.get_pending(session_dir)
approval.approve(session_dir, pending.request_id, event_log=log)
# orchestrator polls resolutions.jsonl for approved snapshot

# S8 orchestrator after approved resolution
if resolution.decision == "approved":
    # use resolution.persona, resolution.cli, resolution.prompt, resolution.teammate_name
    backend.split_pane(..., command=spawn_cmd, cwd=project_path)
```
