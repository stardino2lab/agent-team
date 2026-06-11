# S3 API Sketch — CLI Core

Review input for 5-expert gate. Implementation follows after BLOCKING=0.

## Design decisions

| Item | Decision |
|------|----------|
| Session root | `AGENT_TEAM_HOME` env → `SessionStore.base_dir`; default `~/.agent-team` |
| `--as NAME` | Sender on `mail send`, inbox recipient on `mail read`; default `lead` |
| `--since last` | Cursor: `{session_dir}/.cli/mail-cursor-{recipient}.json` with `{"ts":"ISO8601Z","last_id":"uuid"}` |
| After `mail read` | Update cursor to max message `ts` in result set |
| Mutations | CLI passes `event_log=EventLog()` on mail send, task create/claim/complete |
| `logs --follow` | Poll loop; tests set `AGENT_TEAM_FOLLOW_ONCE=1` for single iteration |
| Output | Human-readable lines (not JSON) for S3 |

## Click tree

```
agent-team
├── init
├── mail send  --session ID --to NAME --body TEXT [--as NAME]
├── mail read  --session ID [--as NAME] [--since last|ISO]
├── task create --session ID --title TEXT [--description] [--deps id,id]
├── task list   --session ID
├── task claim  --session ID --id TASK_ID --assignee NAME
├── task complete --session ID --id TASK_ID
├── logs tail   --session ID [--lines N] [--follow]
├── logs export --session ID --to PATH
├── personas list [--project PATH]
└── context show [--project PATH] [--playbook NAME]
```

## `cli/_helpers.py`

```python
def resolve_base_dir() -> Path
def resolve_session_dir(session_id: str) -> Path  # exists + session.json
def mail_cursor_path(session_dir: Path, recipient: str) -> Path
def load_mail_cursor(session_dir, recipient) -> str | None
def save_mail_cursor(session_dir, recipient, *, ts: str, last_id: str) -> None
def read_mail_messages(session_dir, recipient, since: str | None) -> list[Message]
def echo_error(msg: str) -> NoReturn  # stderr, exit 1
```

## `session.py` change

```python
def default_base_dir() -> Path:
    if home := os.environ.get("AGENT_TEAM_HOME"):
        return Path(home)
    return Path.home() / ".agent-team"
```

## Module mapping

| CLI | Library |
|-----|---------|
| mail send | `mailbox.send(..., from_=as, event_log=EventLog())` |
| mail read | `read_inbox(..., since=resolved)` + cursor update |
| task * | `tasks.*` + EventLog on mutations |
| logs tail | `EventLog().tail(session_dir, n=lines)` |
| logs export | `shutil.copy2(events.jsonl, to)` |
| personas list | `PersonaRegistry(project_path=...).list_personas()` |
| context show | `ProjectLoader(project).build_lead_context(...)` |

## Error → exit 1

`SessionNotFoundError`, missing session dir, `TaskDependencyError`, `TaskStateError`, `InvalidPathSegmentError`, `ProjectConfigError`, `TeamMdNotFoundError`, `PlaybookNotFoundError`

## Test matrix (7)

| Test | Scenario |
|------|----------|
| mail send/read | send + read --as lead |
| mail since last | two sends, second only via --since last |
| task lifecycle | create/list/claim/complete |
| logs tail | mail_sent in tail |
| logs export | file at --to |
| personas list | contains planner |
| context show | TEAM.md section in output |

Fixtures: `AGENT_TEAM_HOME` + `session_store` create session before CLI invoke.
