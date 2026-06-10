# S1 API Sketch — Core Data Layer

Review input for 4-expert gate. Implementation follows this sketch after BLOCKING=0.

## Design principles

| Item | Decision |
|------|----------|
| Storage root | `{base_dir}/sessions/{session_id}/` — prod default `~/.agent-team`, tests use `tmp_path` |
| Serialization | stdlib `json` only (no new S1 deps) |
| Types | `@dataclass` + `Literal` for states; Python 3.12 type hints |
| Timestamps | UTC ISO8601 with `Z` suffix |
| Message ID | `uuid4()` string |
| Task ID | `task-{NNN}` auto-increment via dir scan (`task-001`, `task-002`, …) |
| Coupling | Mailbox/TaskBoard accept optional `EventLog` inject for test isolation |
| Writes | Direct `write_text` / append (single-process S1; atomic rename deferred to S7) |

## Shared utilities (`src/agent_team/_io.py`)

```python
def safe_segment(name: str, label: str) -> str   # ^[a-zA-Z0-9._-]+$; raises InvalidPathSegmentError
def utc_now() -> datetime
def format_ts(dt: datetime) -> str          # "2026-06-10T12:00:00Z"
def parse_ts(value: str) -> datetime        # accepts ISO with Z or +00:00
def parse_since(since: datetime | str | None) -> datetime | None  # naive → UTC
def write_json(path: Path, data: dict) -> None
def read_json(path: Path) -> dict
```

`session_id`, `recipient`, `task_id` validated via `safe_segment` before path join.

---

## `session.py` — SessionStore

### Dataclasses

```python
@dataclass
class Member:
    name: str
    role: Literal["lead", "teammate"]
    persona: str | None
    cli: str
    pane_id: str | None
    backend: str
    status: str

@dataclass
class Session:
    session_id: str
    project_path: str
    psmux_session: str
    playbook: str | None
    playbook_mode: str          # default "guide"
    created_at: str               # ISO8601 Z
    status: str                   # default "active"
    members: list[Member]
    max_teammates: int            # default 5
```

### JSON mapping

- `Member` ↔ JSON object fields match IMPLEMENTATION §session.json
- `persona`, `pane_id`, `assignee`-like nulls serialize as JSON `null`

### SessionStore

```python
class SessionStore:
    def __init__(self, base_dir: Path | None = None) -> None
        # default: Path.home() / ".agent-team"

    def session_dir(self, session_id: str) -> Path
        # → base_dir / "sessions" / session_id

    def ensure_layout(self, session_id: str) -> Path
        # creates mailbox/, tasks/, approval/; returns session_dir

    def create(
        self,
        *,
        session_id: str,
        project_path: str,
        psmux_session: str,
        playbook: str | None = None,
        playbook_mode: str = "guide",
        members: list[Member] | None = None,
        max_teammates: int = 5,
        status: str = "active",
    ) -> Session
        # ensure_layout + write session.json

    def load(self, session_id: str) -> Session
        # raises SessionNotFoundError if missing

    def save(self, session: Session) -> None

    def update_members(self, session_id: str, members: list[Member]) -> Session
```

### Exceptions

| Exception | When |
|-----------|------|
| `SessionNotFoundError` | `load()` — no session.json |
| `SessionExistsError` | `create()` — session dir already has session.json |

---

## `mailbox.py` — Mailbox

### Dataclass

```python
@dataclass
class Message:
    id: str
    from_: str       # JSON key "from"
    to: str
    body: str
    ts: str
```

### Functions

```python
def send(
    session_dir: Path,
    *,
    from_: str,
    to: str,
    body: str,
    event_log: EventLog | None = None,
) -> Message
    # append to mailbox/{to}.jsonl
    # if event_log: append mail_sent

def read_inbox(
    session_dir: Path,
    recipient: str,
    since: datetime | str | None = None,
) -> list[Message]
    # since: None = all; str = ISO8601; datetime = filter ts > since (exclusive)
    # missing inbox file → []
```

### JSON line

```json
{"id":"uuid","from":"lead","to":"planner-1","body":"...","ts":"2026-06-10T12:01:00Z"}
```

---

## `tasks.py` — TaskBoard

### Dataclass

```python
TaskState = Literal["pending", "in_progress", "completed"]

@dataclass
class Task:
    id: str
    title: str
    description: str
    state: TaskState
    deps: list[str]
    assignee: str | None
    created_at: str
    updated_at: str
```

### Functions

```python
def _next_task_id(session_dir: Path) -> str
    # scan tasks/task-*.json; parse numeric suffix; skip malformed names
    # empty dir → task-001; max 0 → task-001; max 5 → task-006

def create_task(
    session_dir: Path,
    *,
    title: str,
    description: str = "",
    deps: list[str] | None = None,
    event_log: EventLog | None = None,
) -> Task
    # writes tasks/{id}.json; event: task_created

def list_tasks(session_dir: Path) -> list[Task]
    # sorted by id

def get_task(session_dir: Path, task_id: str) -> Task
    # raises TaskNotFoundError

def claim_task(
    session_dir: Path,
    task_id: str,
    assignee: str,
    event_log: EventLog | None = None,
) -> Task
    # missing dep task → TaskNotFoundError; incomplete dep → TaskDependencyError
    # all deps completed; sets assignee + in_progress; event: task_claimed

def complete_task(
    session_dir: Path,
    task_id: str,
    event_log: EventLog | None = None,
) -> Task
    # state → completed; event: task_completed
```

### Exceptions

| Exception | When |
|-----------|------|
| `TaskNotFoundError` | get/claim/complete — missing file |
| `TaskDependencyError` | claim — dep not completed |
| `TaskStateError` | claim on non-pending; complete on non-in_progress |

---

## `event_log.py` — EventLog

### Dataclass

```python
@dataclass
class Event:
    type: str
    ts: str
    payload: dict
```

### EventLog class

```python
class EventLog:
    def append(
        self,
        session_dir: Path,
        *,
        type_: str,
        payload: dict,
        ts: datetime | None = None,
    ) -> Event

    def read(
        self,
        session_dir: Path,
        since: datetime | str | None = None,
    ) -> list[Event]
        # since filter: exclusive ts > since (same as read_inbox)

    def tail(self, session_dir: Path, n: int = 50) -> list[Event]
        # last n events chronologically
```

### Event type minimum payloads (S1 writers)

| type | payload keys |
|------|--------------|
| `session_started` | `session_id`, `project_path` |
| `mail_sent` | `from`, `to`, `id` |
| `task_created` | `task_id`, `title` |
| `task_claimed` | `task_id`, `assignee` |
| `task_completed` | `task_id` |
| `spawn_requested` | `persona`, `cli`, `requested_by` |
| `spawn_approved` | `request_id`, `persona` |
| `spawn_denied` | `request_id` |
| `teammate_ready` | `name`, `pane_id` |
| `teammate_shutdown` | `name` |
| `error` | `message`, `context?` |

S1 modules only emit: `mail_sent`, `task_created`, `task_claimed`, `task_completed`. Others reserved for S5+.

---

## `tests/conftest.py` fixtures

```python
@pytest.fixture
def sessions_base(tmp_path: Path) -> Path:
    return tmp_path / "agent-team"

@pytest.fixture
def session_store(sessions_base: Path) -> SessionStore:
    return SessionStore(base_dir=sessions_base)

@pytest.fixture
def session_dir(session_store: SessionStore) -> Path:
    session = session_store.create(
        session_id="test-session",
        project_path="c:\\DEV\\test",
        psmux_session="test-session",
        members=[Member(name="lead", role="lead", persona=None, cli="claude",
                        pane_id="%0", backend="psmux", status="running")],
    )
    return session_store.session_dir(session.session_id)
```

---

## Test matrix (12+)

| Module | Test | Count |
|--------|------|-------|
| session | create layout + session.json | 1 |
| session | load round-trip members | 1 |
| mailbox | send appends jsonl | 1 |
| mailbox | read_inbox all | 1 |
| mailbox | read_inbox since filter | 1 |
| mailbox | send + event mail_sent | 1 |
| tasks | create + list | 1 |
| tasks | claim sets assignee/state | 1 |
| tasks | claim blocked by deps | 1 |
| tasks | complete | 1 |
| event_log | append multiple | 1 |
| event_log | since + tail | 1 |

Total: 12 minimum.

---

## Downstream compatibility notes (S3/S6/S7)

- S3 `mail read --since last|ISO` → `read_inbox(since=...)`
- S3 `task claim|complete` → `claim_task` / `complete_task`
- S3 `logs tail` → `EventLog.tail` / `read`
- S6 MCP `send_message` → `mailbox.send` + default `EventLog()`
- S6 MCP `create_task` / `claim_task` / `complete_task` → tasks module
- S6 MCP `read_messages` → `read_inbox(session_dir, "lead", since)`
- S7 TUI watches `events.jsonl`, `mailbox/*.jsonl`, `tasks/*.json`
