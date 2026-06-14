# S11a — $20-lead hardening (D6 + D8 + D9): Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the $20 Claude lead's low-token property *structural* — lock it to orchestration-only (D6), give it a single blocking event-driven wait instead of shell-loop polling (D8), and bound/filter every read it performs (D9).

**Architecture:** Three independent seams, no new modules. **D6** prepends a CLI-agnostic orchestration-only preamble in `ProjectLoader.build_lead_context`. **D8** adds two MCP tools — non-blocking `get_recent_events(since, limit)` and blocking `wait_for_event(types, since, timeout)` backed by `events.jsonl`, the latter event-driven via the existing `watchfiles` dependency (immediate-check → watch `session_dir` → deadline-bounded). **D9** adds a `from_` filter to `read_inbox`/`read_messages`, a tail `limit` to `EventLog.read`, and a generous tail bound to `Orchestrator.reconcile_handled`. Reference spec: `docs/s11-multi-cli-plan.md` (decisions **D6**, **D8**, **D9**; preamble exact text at "Lead orchestration-only preamble (D6) — exact text").

**Tech Stack:** Python 3.12, pytest, ruff. `watchfiles` (already a dependency — see `src/agent_team/_watcher.py`). psmux backend mocked (`PsmuxBackend(mock=True)`). Tests use `tmp_path` + shared fixtures in `tests/conftest.py` (`session_store`, `session_dir`, `event_log`, `consumer_project`, `mcp_context`, `psmux_backend`, `persona_registry`).

---

## Design decisions resolved before this plan (user-confirmed)

1. **`wait_for_event` mechanism = watchfiles event-driven** (not server-side poll). Immediate match-check, then `watchfiles.watch(session_dir, …)` with a `rust_timeout` safety slice + `yield_on_timeout`, bounded by a monotonic deadline. Reuses the proven `_watcher.py` dependency; ~zero idle CPU; the lead makes ONE blocking call and burns no tokens while waiting.
2. **`reconcile_handled` tail = generous `limit` (2000)**, honoring the committed D9 text. Correctness rests on `session.json`: the `member.request_id` and `teammate_name` handled-signals are read from the *complete* session (not the log), so a `teammate_ready`/`error` event aging past 2000 entries can, at worst, cause one redundant `error` re-log on attach — **never a double-spawn** (a spawned teammate persists as a member). Documented here for the expert gate.
3. **D6 preamble = the spec's exact text PLUS** a D8 no-shell-polling line (pointing the lead at `wait_for_event`) and a terse-output line — because D8/D6 both land in S11a.
4. **Tool count**: S11a adds 2 MCP tools → **11 total**. Forward-looking "9 tools" references in `docs/s11-multi-cli-plan.md` are updated to 11 (Task 7). Historical S6 records (`docs/s6-api-sketch.md`, `docs/STATUS.ko.md`) are left as-is.

---

## File Structure

- Modify: `src/agent_team/project_loader.py` — add module constant `LEAD_ORCHESTRATION_PREAMBLE`; prepend it as the first section in `build_lead_context` (before `--- TEAM.md ---`). **(D6)**
- Modify: `src/agent_team/event_log.py` — add `limit: int | None = None` to `EventLog.read` (tail after `since` filtering); make `tail` delegate to `read(limit=n)`. **(D9)**
- Modify: `src/agent_team/mailbox.py` — add `from_: str | None = None` to `read_inbox` (exact-sender filter, composes with `since`). **(D9)**
- Modify: `src/agent_team/mcp_server.py` — thread `from_` through `handle_read_messages` + the `read_messages` tool **(D9)**; add `handle_get_recent_events` + `handle_wait_for_event` handlers and `get_recent_events` + `wait_for_event` `@mcp.tool()` wrappers, plus `_event_to_dict`, `_matching_events`, and module constants `_DEFAULT_WAIT_TIMEOUT`/`_WAIT_SAFETY_SLICE_MS` **(D8)**. New imports: `threading`, `time`, `watchfiles`.
- Modify: `src/agent_team/orchestrator.py` — add module constant `_RECONCILE_EVENT_TAIL = 2000`; pass `limit=_RECONCILE_EVENT_TAIL` to the `event_log.read` call in `reconcile_handled` (line 316). **(D9)**
- Test: `tests/unit/test_project_loader.py`, `tests/unit/test_event_log.py`, `tests/unit/test_mailbox.py`, `tests/unit/test_mcp_server.py`, `tests/unit/test_orchestrator.py`.
- Docs: `docs/s11-multi-cli-plan.md` (9→11 tools), `PROGRESS.md` (S11a entry).

**Task order & dependencies:** Task 1 (D6) and Tasks 2/3 (D9 leaf changes) are independent. Task 4 (`get_recent_events`) depends on Task 2 (`read(limit=)`). Task 5 (`wait_for_event`) is independent of Task 4 but shares the helpers it introduces — do Task 4 first. Task 6 (reconcile tail) depends on Task 2. Task 7 (docs) last.

---

## Task 1: D6 — lead orchestration-only preamble

**Files:**
- Modify: `src/agent_team/project_loader.py`
- Test: `tests/unit/test_project_loader.py`

- [ ] **Step 1: Write the failing test**

In `tests/unit/test_project_loader.py`, add (import `ProjectLoader` is already at the top of the file):

```python
def test_build_lead_context_prepends_orchestration_preamble(consumer_project: Path) -> None:
    loader = ProjectLoader(consumer_project)
    ctx = loader.build_lead_context()

    text = ctx.text
    # D6: locks the low-token property structurally — lead orchestrates, never codes.
    assert "You are the team LEAD" in text
    assert "NEVER read, edit, write, or review project code yourself" in text
    # D8 line folded into the preamble: no shell-loop polling, use wait_for_event.
    assert "Do NOT poll with shell loops" in text
    assert "wait_for_event" in text
    # D9 line: tell the lead to filter reads, not pull everything.
    assert "since/from_/limit" in text
    # Terse-output line (D6 verbose-self-summary fix).
    assert "terse" in text.lower()
    # The preamble frames the prompt — it must come BEFORE the project material.
    assert text.index("You are the team LEAD") < text.index("--- TEAM.md ---")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/unit/test_project_loader.py::test_build_lead_context_prepends_orchestration_preamble -v`
Expected: FAIL — `build_lead_context` has no role framing today; "You are the team LEAD" is absent.

- [ ] **Step 3: Add the preamble constant**

In `src/agent_team/project_loader.py`, after the imports (after line 10, the `from agent_team._io import …` line) and before `class ProjectConfigError`, add:

```python
# Prepended to every lead system prompt (claude, codex, or any future gated CLI)
# so the lead's low-token property is STRUCTURAL, not a playbook convention. A
# custom TEAM.md/playbook saying "review the code yourself" cannot turn the lead
# into a high-token consumer. The text below is the spec's D6 block (see
# docs/s11-multi-cli-plan.md) plus the D8 no-shell-polling line and a terse-output
# line, since D6/D8 land together in S11a.
LEAD_ORCHESTRATION_PREAMBLE = """\
You are the team LEAD. Your only job is orchestration — not coding.

- Coordinate the team EXCLUSIVELY through the agent-team MCP tools:
  spawn_teammate, send_message, create_task, claim_task, complete_task, list_teammates.
- NEVER read, edit, write, or review project code yourself. Delegate every file read,
  edit, test run, and code review to a teammate — that is what teammates are for.
- Your only outputs are: spawn/approval decisions, task assignments, mail to teammates,
  and a final synthesis built from teammates' MAILED findings (never from raw files/diffs).
- Keep your context lean. Do not pull large files, diffs, or logs into your own context.
  If code must be understood, spawn a teammate to read it and mail you a short summary.
- Do NOT poll with shell loops or background watchers to wait for a stage to finish.
  Call wait_for_event(types, since, timeout) to block until teammates signal progress
  (teammate_ready / task_completed / mail_sent), or get_recent_events(since, limit) to
  catch up. The orchestrator emits these events for you — never arm a shell `test -f` loop.
- When reading mail or events, filter — pass since/from_/limit instead of pulling the
  whole inbox or event log into your context.
- Treat the playbook as a guide, and honor the config allowlists (max_teammates,
  allowed_personas). Spawn only with user approval; shut teammates down when their stage ends.
- Keep your own messages terse. No multi-paragraph recaps — a few lines suffice."""
```

- [ ] **Step 4: Prepend the preamble in `build_lead_context`**

In `src/agent_team/project_loader.py`, in `build_lead_context`, change the `sections` list initializer (currently lines 91-98) so the preamble is the first section:

```python
        sections = [
            LEAD_ORCHESTRATION_PREAMBLE,
            "--- TEAM.md ---",
            team_md,
            "--- Project config ---",
            f"max_teammates: {config.get('max_teammates', 5)}",
            f"playbook_mode: {config.get('playbook_mode', 'guide')}",
            f"allowed_personas: {config.get('allowed_personas', [])}",
        ]
```

- [ ] **Step 5: Run the targeted + existing project_loader tests**

Run: `python -m pytest tests/unit/test_project_loader.py -v`
Expected: PASS — the new test passes; `test_build_lead_context_sections` still passes (it asserts the `--- …---` markers and `extra_context`, all unaffected by a prepended block).

- [ ] **Step 6: Commit**

```bash
git add src/agent_team/project_loader.py tests/unit/test_project_loader.py
git commit -m "feat(s11a): D6 lead orchestration-only preamble

Prepend a CLI-agnostic 'you are the LEAD, orchestrate only' preamble to every
lead system prompt in build_lead_context. Locks the \$20-lead low-token property
structurally (no playbook can turn the lead into a coder). Includes the D8
no-shell-polling line (use wait_for_event) and a terse-output line.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: D9 — `EventLog.read(limit=)` tail

**Files:**
- Modify: `src/agent_team/event_log.py`
- Test: `tests/unit/test_event_log.py`

- [ ] **Step 1: Write the failing test**

In `tests/unit/test_event_log.py`, add (imports `EventLog`, `datetime`, `timedelta`, `Path` already present):

```python
def test_read_limit_tails_after_since(session_dir: Path, event_log: EventLog) -> None:
    t0 = datetime.fromisoformat("2026-06-10T12:00:00+00:00")
    for i in range(5):
        event_log.append(
            session_dir,
            type_="task_created",
            payload={"i": i},
            ts=t0 + timedelta(seconds=i),
        )

    # limit alone returns the last N in order.
    last2 = event_log.read(session_dir, limit=2)
    assert [e.payload["i"] for e in last2] == [3, 4]

    # limit composes with since: filter first, then tail.
    after = event_log.read(session_dir, since=t0, limit=2)
    assert [e.payload["i"] for e in after] == [3, 4]

    # limit larger than the set returns everything.
    assert len(event_log.read(session_dir, limit=99)) == 5

    # tail() still works (now delegates to read(limit=n)).
    assert [e.payload["i"] for e in event_log.tail(session_dir, n=2)] == [3, 4]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/unit/test_event_log.py::test_read_limit_tails_after_since -v`
Expected: FAIL — `read()` has no `limit` parameter (`TypeError: read() got an unexpected keyword argument 'limit'`).

- [ ] **Step 3: Add `limit` to `read` and delegate `tail`**

In `src/agent_team/event_log.py`, replace the `read` and `tail` methods (currently lines 40-63) with:

```python
    def read(
        self,
        session_dir: Path,
        since: datetime | str | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        path = self._path(session_dir)
        if not path.exists():
            return []

        since_dt = parse_since(since)
        events: list[Event] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            event = Event(type=data["type"], ts=data["ts"], payload=data["payload"])
            if since_dt is not None and parse_ts(event.ts) <= since_dt:
                continue
            events.append(event)
        # Tail bound: a long-running session re-reads only the most recent
        # `limit` events instead of the whole log. Applied AFTER `since` so the
        # window is "the last N matching events", not "N then filter".
        if limit is not None:
            return events[-limit:]
        return events

    def tail(self, session_dir: Path, n: int = 50) -> list[Event]:
        return self.read(session_dir, limit=n)
```

- [ ] **Step 4: Run the targeted + existing event_log tests**

Run: `python -m pytest tests/unit/test_event_log.py -v`
Expected: PASS — new test green; `test_read_since_and_tail` and the other existing tests unaffected (default `limit=None` preserves behavior; `tail` output is identical to the old `read()[-n:]`).

- [ ] **Step 5: Commit**

```bash
git add src/agent_team/event_log.py tests/unit/test_event_log.py
git commit -m "feat(s11a): D9 EventLog.read(limit=) tail bound

Add an optional tail limit to EventLog.read (applied after the since filter);
tail() now delegates to read(limit=n). Lets long-running sessions re-ingest only
recent events instead of the whole log.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: D9 — `read_messages` `from_` filter

**Files:**
- Modify: `src/agent_team/mailbox.py`, `src/agent_team/mcp_server.py`
- Test: `tests/unit/test_mailbox.py`, `tests/unit/test_mcp_server.py`

- [ ] **Step 1: Write the failing tests**

In `tests/unit/test_mailbox.py`, add (it imports `send`, `read_inbox` from `agent_team.mailbox` — confirm/extend the existing import line):

```python
def test_read_inbox_from_filter(session_dir: Path) -> None:
    send(session_dir, from_="helper-1", to="lead", body="a")
    send(session_dir, from_="helper-2", to="lead", body="b")
    send(session_dir, from_="helper-1", to="lead", body="c")

    only_h1 = read_inbox(session_dir, "lead", from_="helper-1")
    assert [m.body for m in only_h1] == ["a", "c"]
    assert read_inbox(session_dir, "lead", from_="helper-2")[0].body == "b"
    # No filter still returns everything.
    assert len(read_inbox(session_dir, "lead")) == 3
```

In `tests/unit/test_mcp_server.py`, first add a module-level import near the existing imports (top of file): `from agent_team.mailbox import send as mailbox_send`. Then add (it already imports `handle_read_messages`, `handle_send_message`, `McpContext`):

```python
def test_read_messages_from_filter(mcp_context: McpContext) -> None:
    mailbox_send(mcp_context.session_dir, from_="helper-1", to="lead", body="a")
    mailbox_send(mcp_context.session_dir, from_="helper-2", to="lead", body="b")

    all_msgs = handle_read_messages(mcp_context)["messages"]
    assert len(all_msgs) == 2
    h1 = handle_read_messages(mcp_context, from_="helper-1")["messages"]
    assert [m["body"] for m in h1] == ["a"]
    assert h1[0]["from"] == "helper-1"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/unit/test_mailbox.py::test_read_inbox_from_filter tests/unit/test_mcp_server.py::test_read_messages_from_filter -v`
Expected: FAIL — `read_inbox()` and `handle_read_messages()` have no `from_` parameter (`TypeError: unexpected keyword argument 'from_'`).

- [ ] **Step 3: Add `from_` to `read_inbox`**

In `src/agent_team/mailbox.py`, replace `read_inbox` (currently lines 75-94) with:

```python
def read_inbox(
    session_dir: Path,
    recipient: str,
    since: datetime | str | None = None,
    from_: str | None = None,
) -> list[Message]:
    safe_segment(recipient, "recipient")
    inbox = session_dir / "mailbox" / f"{recipient}.jsonl"
    if not inbox.exists():
        return []

    since_dt = parse_since(since)
    messages: list[Message] = []
    for line in inbox.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        message = _message_from_dict(json.loads(line))
        if since_dt is not None and parse_ts(message.ts) <= since_dt:
            continue
        if from_ is not None and message.from_ != from_:
            continue
        messages.append(message)
    return messages
```

- [ ] **Step 4: Thread `from_` through the MCP handler + tool**

In `src/agent_team/mcp_server.py`, replace `handle_read_messages` (currently lines 206-219) with:

```python
def handle_read_messages(
    ctx: McpContext, since: str | None = None, from_: str | None = None
) -> dict:
    messages = read_inbox(ctx.session_dir, "lead", since=since, from_=from_)
    return {
        "messages": [
            {
                "id": m.id,
                "from": m.from_,
                "to": m.to,
                "body": m.body,
                "ts": m.ts,
            }
            for m in messages
        ]
    }
```

And replace the `read_messages` tool wrapper (currently lines 296-299) with:

```python
@mcp.tool()
def read_messages(since: str | None = None, from_: str | None = None) -> dict:
    """Read lead inbox messages, optionally filtered by ISO timestamp and/or sender."""
    return _run_tool(handle_read_messages, since, from_)
```

- [ ] **Step 5: Run the targeted + existing mailbox/mcp tests**

Run: `python -m pytest tests/unit/test_mailbox.py tests/unit/test_mcp_server.py -v`
Expected: PASS — new tests green; `test_read_messages_since_filter` and the existing mailbox `since` tests unaffected (default `from_=None`).

- [ ] **Step 6: Commit**

```bash
git add src/agent_team/mailbox.py src/agent_team/mcp_server.py tests/unit/test_mailbox.py tests/unit/test_mcp_server.py
git commit -m "feat(s11a): D9 read_messages from_ filter

read_inbox + handle_read_messages + the read_messages MCP tool gain an exact
sender filter that composes with since, so the lead can pull just one teammate's
mail instead of the whole inbox.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: D8 — `get_recent_events` MCP tool

**Files:**
- Modify: `src/agent_team/mcp_server.py`
- Test: `tests/unit/test_mcp_server.py`

**Depends on Task 2** (`EventLog.read(limit=)`).

- [ ] **Step 1: Write the failing test**

In `tests/unit/test_mcp_server.py`, add (it imports `format_ts`, `parse_ts` already; add `from datetime import timedelta` is already present at top):

```python
def test_get_recent_events_returns_since_and_limit(mcp_context: McpContext) -> None:
    from agent_team.mcp_server import handle_get_recent_events

    sd = mcp_context.session_dir
    el = mcp_context.event_log
    el.append(sd, type_="session_started", payload={"n": 0})
    el.append(sd, type_="mail_sent", payload={"n": 1})
    el.append(sd, type_="teammate_ready", payload={"n": 2})

    all_evt = handle_get_recent_events(mcp_context)["events"]
    assert [e["type"] for e in all_evt] == ["session_started", "mail_sent", "teammate_ready"]
    assert all_evt[0]["payload"] == {"n": 0}
    assert all_evt[0]["ts"].endswith("Z")

    # limit tails.
    assert [e["payload"]["n"] for e in handle_get_recent_events(mcp_context, limit=2)["events"]] == [1, 2]

    # since filters (exclusive, matching EventLog.read).
    cutoff = all_evt[1]["ts"]
    later = handle_get_recent_events(mcp_context, since=cutoff)["events"]
    assert [e["payload"]["n"] for e in later] == [2]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/unit/test_mcp_server.py::test_get_recent_events_returns_since_and_limit -v`
Expected: FAIL — `handle_get_recent_events` does not exist (`ImportError`).

- [ ] **Step 3: Add the event-dict helper + handler**

In `src/agent_team/mcp_server.py`, add after `handle_list_teammates` (currently ends line 261), before `def _run_tool`:

```python
def _event_to_dict(event) -> dict:
    return {"type": event.type, "ts": event.ts, "payload": event.payload}


def handle_get_recent_events(
    ctx: McpContext, since: str | None = None, limit: int | None = None
) -> dict:
    events = ctx.event_log.read(ctx.session_dir, since=since, limit=limit)
    return {"events": [_event_to_dict(e) for e in events]}
```

- [ ] **Step 4: Add the `get_recent_events` tool wrapper**

In `src/agent_team/mcp_server.py`, add after the `read_messages` tool wrapper:

```python
@mcp.tool()
def get_recent_events(since: str | None = None, limit: int | None = None) -> dict:
    """Read recent coordination events (teammate_ready/task_*/mail_sent), newest-bounded.

    Non-blocking catch-up. Pass `since` (ISO ts) to get only newer events and
    `limit` to cap how many are returned. Use wait_for_event to BLOCK for the next one.
    """
    return _run_tool(handle_get_recent_events, since, limit)
```

- [ ] **Step 5: Run the targeted + existing mcp tests**

Run: `python -m pytest tests/unit/test_mcp_server.py -v`
Expected: PASS — new test green; existing tests unaffected.

- [ ] **Step 6: Commit**

```bash
git add src/agent_team/mcp_server.py tests/unit/test_mcp_server.py
git commit -m "feat(s11a): D8 get_recent_events MCP tool

Non-blocking events.jsonl catch-up for the lead (since + limit), so it reads the
orchestrator's coordination trail via one bounded tool call instead of re-reading
files or arming watchers.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: D8 — `wait_for_event` MCP tool (watchfiles, event-driven)

**Files:**
- Modify: `src/agent_team/mcp_server.py`
- Test: `tests/unit/test_mcp_server.py`

**Depends on Task 4** (`_event_to_dict` helper).

- [ ] **Step 1: Write the failing tests**

In `tests/unit/test_mcp_server.py`, add (`import threading`, `import time` at the top of the file if absent):

```python
def test_wait_for_event_returns_existing_match(mcp_context: McpContext) -> None:
    from agent_team.mcp_server import handle_wait_for_event

    mcp_context.event_log.append(
        mcp_context.session_dir, type_="teammate_ready", payload={"name": "helper-1"}
    )
    result = handle_wait_for_event(
        mcp_context, types=["teammate_ready"], timeout=5.0
    )
    assert result["timed_out"] is False
    assert [e["type"] for e in result["events"]] == ["teammate_ready"]


def test_wait_for_event_times_out(mcp_context: McpContext) -> None:
    from agent_team.mcp_server import handle_wait_for_event

    result = handle_wait_for_event(
        mcp_context, types=["teammate_ready"], timeout=0.3
    )
    assert result["timed_out"] is True
    assert result["events"] == []


def test_wait_for_event_ignores_other_types(mcp_context: McpContext) -> None:
    from agent_team.mcp_server import handle_wait_for_event

    mcp_context.event_log.append(
        mcp_context.session_dir, type_="mail_sent", payload={"id": "x"}
    )
    result = handle_wait_for_event(
        mcp_context, types=["teammate_ready"], timeout=0.3
    )
    assert result["timed_out"] is True
    assert result["events"] == []


def test_wait_for_event_wakes_on_new_event(mcp_context: McpContext) -> None:
    import threading

    from agent_team.mcp_server import handle_wait_for_event

    sd = mcp_context.session_dir
    el = mcp_context.event_log
    # Append the event ~0.3s into the wait; the watcher must wake well before the
    # 5s timeout. Generous timeout keeps this robust on slow CI.
    timer = threading.Timer(
        0.3, lambda: el.append(sd, type_="teammate_ready", payload={"name": "helper-1"})
    )
    timer.start()
    try:
        result = handle_wait_for_event(
            mcp_context, types=["teammate_ready"], timeout=5.0
        )
    finally:
        timer.cancel()

    assert result["timed_out"] is False
    assert any(e["type"] == "teammate_ready" for e in result["events"])


def test_wait_for_event_rejects_empty_types(mcp_context: McpContext) -> None:
    from agent_team.mcp_server import McpToolError, handle_wait_for_event

    with pytest.raises(McpToolError):
        handle_wait_for_event(mcp_context, types=[], timeout=0.3)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/unit/test_mcp_server.py -k wait_for_event -v`
Expected: FAIL — `handle_wait_for_event` does not exist (`ImportError`).

- [ ] **Step 3: Add imports + wait constants + matcher**

In `src/agent_team/mcp_server.py`, add to the imports block at the top (after `import os`, keeping alphabetical-ish grouping with the stdlib imports):

```python
import threading
import time
```

and after the third-party import line `from mcp.server.fastmcp import FastMCP`, add:

```python
import watchfiles
```

Then, after `_event_to_dict` (from Task 4), add the matcher + constants:

```python
# wait_for_event tuning. The lead makes ONE blocking call and burns no tokens
# while it waits, replacing shell-loop polling (D8). watchfiles wakes immediately
# (~50ms) on a real events.jsonl write via OS notifications; _WAIT_SAFETY_SLICE_MS
# only bounds the idle re-check cadence and the tiny write-between-immediate-check-
# and-watch-start race window. 500ms keeps worst-case race recovery snappy while
# idle re-reads stay negligible (a few file reads, lead burns no tokens).
_DEFAULT_WAIT_TIMEOUT = 60.0
_WAIT_SAFETY_SLICE_MS = 500


def _matching_events(ctx: McpContext, types: list[str], since: str | None) -> list:
    wanted = set(types)
    return [
        e for e in ctx.event_log.read(ctx.session_dir, since=since) if e.type in wanted
    ]
```

- [ ] **Step 4: Add the `handle_wait_for_event` handler**

In `src/agent_team/mcp_server.py`, add after `handle_get_recent_events`:

```python
def handle_wait_for_event(
    ctx: McpContext,
    types: list[str],
    since: str | None = None,
    timeout: float | None = None,
) -> dict:
    if not types:
        raise McpToolError("wait_for_event requires at least one event type")
    timeout = _DEFAULT_WAIT_TIMEOUT if timeout is None else float(timeout)

    matches = _matching_events(ctx, types, since)
    if matches:
        return {"events": [_event_to_dict(e) for e in matches], "timed_out": False}

    deadline = time.monotonic() + timeout
    # rust_timeout caps the idle wait per cycle; for short timeouts it equals the
    # whole budget so the call returns promptly instead of after a fixed 2s slice.
    slice_ms = max(1, int(min(timeout, _WAIT_SAFETY_SLICE_MS / 1000) * 1000))
    stop = threading.Event()
    try:
        for _changes in watchfiles.watch(
            ctx.session_dir,
            stop_event=stop,
            rust_timeout=slice_ms,
            yield_on_timeout=True,
        ):
            matches = _matching_events(ctx, types, since)
            if matches:
                return {
                    "events": [_event_to_dict(e) for e in matches],
                    "timed_out": False,
                }
            if time.monotonic() >= deadline:
                break
    finally:
        # Stop the watchfiles Rust thread regardless of how we exit.
        stop.set()
    return {"events": [], "timed_out": True}
```

- [ ] **Step 4b: Widen `_map_tool_error` for I/O errors**

`wait_for_event` touches the filesystem via watchfiles, which can raise `OSError`
(e.g. a transient watch failure). Surface it as readable tool-error text instead of
the opaque "Internal tool error". In `src/agent_team/mcp_server.py`, add `OSError`
to the `isinstance(...)` tuple in `_map_tool_error` (currently lines 113-130), e.g.
right after `PsmuxCommandError,`:

```python
            PsmuxCommandError,
            OSError,
            ValueError,
```

(`McpToolError` is already in the tuple, so the empty-`types` validation maps cleanly.)

- [ ] **Step 5: Add the `wait_for_event` tool wrapper**

In `src/agent_team/mcp_server.py`, add after the `get_recent_events` tool wrapper:

```python
@mcp.tool()
def wait_for_event(
    types: list[str], since: str | None = None, timeout: float | None = None
) -> dict:
    """Block until a coordination event of the given types is emitted, or timeout.

    Event-driven (no polling). Use this to wait for a stage to finish — e.g.
    wait_for_event(["teammate_ready"]) after a spawn, or wait_for_event(
    ["task_completed", "mail_sent"], since=<ts>) for a working teammate — instead
    of arming a shell watcher. Pass `since` (ISO ts) to ignore older events.
    Returns {"events": [...], "timed_out": bool}; timeout defaults to 60s.
    """
    return _run_tool(handle_wait_for_event, types, since, timeout)
```

- [ ] **Step 6: Run the targeted + full mcp tests**

Run: `python -m pytest tests/unit/test_mcp_server.py -v`
Expected: PASS — all four `wait_for_event` tests green; existing tests unaffected. (The timeout test takes ~0.3s; the wakes-on-new test ~0.3s.)

- [ ] **Step 7: Commit**

```bash
git add src/agent_team/mcp_server.py tests/unit/test_mcp_server.py
git commit -m "feat(s11a): D8 wait_for_event MCP tool (event-driven)

Blocking wait backed by events.jsonl via watchfiles: immediate match-check, then
watch session_dir bounded by a monotonic deadline (rust_timeout safety slice +
yield_on_timeout). The lead makes ONE blocking call and burns no tokens while
waiting, replacing shell-loop polling (the single biggest lead-token waste in the
S10 E2E).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: D9 — `reconcile_handled` generous tail

**Files:**
- Modify: `src/agent_team/orchestrator.py`
- Test: `tests/unit/test_orchestrator.py`

**Depends on Task 2** (`EventLog.read(limit=)`).

- [ ] **Step 1: Write the failing test**

In `tests/unit/test_orchestrator.py`, add (it imports `Orchestrator`/`OrchestratorContext`; add `import agent_team.orchestrator as orchestrator_module` at the top if not present):

```python
def test_reconcile_handled_tails_event_read(orchestrator, monkeypatch) -> None:
    import agent_team.orchestrator as orchestrator_module

    captured: dict = {}
    real_read = orchestrator.ctx.event_log.read

    def spy_read(session_dir, since=None, limit=None):
        captured["limit"] = limit
        return real_read(session_dir, since=since, limit=limit)

    monkeypatch.setattr(orchestrator.ctx.event_log, "read", spy_read)
    orchestrator.reconcile_handled()

    # D9: reconcile bounds its events.jsonl ingest with the generous tail constant.
    assert captured["limit"] == orchestrator_module._RECONCILE_EVENT_TAIL
    assert orchestrator_module._RECONCILE_EVENT_TAIL >= 2000
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/unit/test_orchestrator.py::test_reconcile_handled_tails_event_read -v`
Expected: FAIL — `_RECONCILE_EVENT_TAIL` does not exist (`AttributeError`), and `reconcile_handled` calls `read` with no `limit` (`captured["limit"]` would be `None`).

- [ ] **Step 3: Add the tail constant**

In `src/agent_team/orchestrator.py`, after the imports block (after line 23, the `from agent_team.teammate_runner import TeammateRunner` line) and before `def _check_lead_cli_supported`, add:

```python
# Tail bound for reconcile_handled's events.jsonl ingest on attach (D9). Generous
# on purpose: correctness rests on session.json, not the log. The handled-signals
# `member.request_id` and `teammate_name` are read from the COMPLETE session, so a
# teammate_ready/error event aging past this many entries can at worst cause one
# redundant `error` re-log on attach — never a double-spawn (a spawned teammate
# persists as a member). 2000 events ≫ any realistic single session.
_RECONCILE_EVENT_TAIL = 2000
```

- [ ] **Step 4: Apply the tail in `reconcile_handled`**

In `src/agent_team/orchestrator.py`, in `reconcile_handled`, change the event-read loop (currently line 316):

```python
        for event in self.ctx.event_log.read(
            self.ctx.session_dir, limit=_RECONCILE_EVENT_TAIL
        ):
```

- [ ] **Step 5: Run the targeted + existing orchestrator tests**

Run: `python -m pytest tests/unit/test_orchestrator.py -v`
Expected: PASS — the new test green; `test_reconcile_handled_uses_teammate_ready_events_when_name_absent` and `test_reconcile_handled_skips_existing_teammates` still pass (they use few events, far under the 2000 tail, so behavior is identical).

- [ ] **Step 6: Commit**

```bash
git add src/agent_team/orchestrator.py tests/unit/test_orchestrator.py
git commit -m "feat(s11a): D9 reconcile_handled generous event tail

Bound reconcile_handled's events.jsonl ingest with _RECONCILE_EVENT_TAIL=2000 so
a long-running session does not re-read the whole log on attach. Correctness is
preserved by the complete session.json signals (member.request_id / teammate_name);
an aged-out ready/error event at worst re-logs one error, never double-spawns.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Docs — tool count + PROGRESS

**Files:**
- Modify: `docs/s11-multi-cli-plan.md`, `PROGRESS.md`

- [ ] **Step 1: Update forward-looking "9 tools" → "11 tools"**

In `docs/s11-multi-cli-plan.md`, update the three forward-looking references (S11a adds `get_recent_events` + `wait_for_event`):
- The "handshake returned all 9 tools" line (~line 152) → "all 11 tools".
- The G2 gate row "returning **all 9 tools**" (~line 228) → "all 11 tools".
- The MCP-interop smoke "returns the 9 tools" (~line 310) → "returns the 11 tools".

Leave historical S6 records untouched (`docs/s6-api-sketch.md`, `docs/STATUS.ko.md` — they describe what S6 delivered).

- [ ] **Step 2: Add the S11a entry to PROGRESS.md**

In `PROGRESS.md`, add an S11a "done" entry under the appropriate section summarizing D6/D8/D9 (preamble locked, event-driven wait + bounded reads), the new MCP tool count (11), and the baseline check (pytest + ruff). Match the existing PROGRESS entry style.

- [ ] **Step 3: Full verification**

Run: `python -m pytest tests/ -q`
Expected: PASS — baseline 216 + the S11a additions (D6×1, D9-read×1, D9-from_×2, D8-get×1, D8-wait×4, D9-reconcile×1 = ~10 new).

Run: `python -m ruff check src/ tests/`
Expected: `All checks passed!`

- [ ] **Step 4: Commit**

```bash
git add docs/s11-multi-cli-plan.md PROGRESS.md
git commit -m "docs(s11a): tool count 9->11; PROGRESS S11a done

S11a added get_recent_events + wait_for_event MCP tools (D8). Update the
forward-looking handshake/interop tool-count references and record S11a (D6/D8/D9)
in PROGRESS.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage (docs/s11-multi-cli-plan.md):**
- **D6** (orchestration-only preamble, structural low-token lock) → Task 1. Exact spec text + D8 no-polling line + terse line; asserted present & before TEAM.md. ✓
- **D8** (event-driven wait, no polling) → Task 4 (`get_recent_events`) + Task 5 (`wait_for_event`, watchfiles). Preamble line forbidding shell loops → Task 1. ✓
- **D9** (bounded + filtered reads): `read_messages` `from_`/`since` → Task 3 (`since` already existed); `EventLog.read(limit=)` tail → Task 2; `reconcile_handled` tail → Task 6. ✓
- Touch-points table (`mcp_server.py` D8 tools + D9 filter; `event_log.py`/`orchestrator.py` D9; `project_loader.py` D6; test slots) → all covered. ✓
- Verification §1 unit slots (preamble present; get_recent_events/wait_for_event from events.jsonl; read_messages filter; EventLog.read tail) → Tasks 1/2/3/4/5. ✓

**2. Placeholder scan:** No TBD/TODO. Every code step shows complete code. Task 7 Step 2 (PROGRESS entry) is prose-by-design (a changelog line matching existing style), not a code placeholder. ✓

**3. Type consistency:**
- `EventLog.read(session_dir, since=None, limit=None)` defined in Task 2; called with `limit=` in Task 4 (`handle_get_recent_events`), Task 5 (`_matching_events`, no limit) and Task 6 (`reconcile_handled`). Spy in Task 6 matches the 3-arg signature. ✓
- `read_inbox(session_dir, recipient, since=None, from_=None)` defined Task 3; called by `handle_read_messages(ctx, since, from_)` Task 3. ✓
- `_event_to_dict` defined Task 4, used in Tasks 4 & 5. `_matching_events(ctx, types, since)` defined Task 5, used in `handle_wait_for_event`. ✓
- `_RECONCILE_EVENT_TAIL` defined Task 6, referenced by the Task 6 test. `_DEFAULT_WAIT_TIMEOUT`/`_WAIT_SAFETY_SLICE_MS` defined & used in Task 5. ✓
- Tool param naming: `from_` matches the D9 spec text (trailing underscore avoids the `from` keyword) — flagged for the expert gate as a possible UX nit. ✓

## Expert plan-review axes (run BEFORE implementing — BLOCKING=0 to proceed)

Per `.cursor/skills/review-expert` (plan mode). Candidate axes for this diff:
- **E1 API / MCP surface** — new tool signatures (`get_recent_events`, `wait_for_event`, `read_messages` `from_`), response shapes, `from_` param-name UX, `_run_tool` error mapping fit, no scope creep.
- **E2 Concurrency / reliability** — `wait_for_event` watchfiles correctness (deadline bound, rust_timeout slice math, write-between-check-and-watch race, Rust-thread cleanup via `stop.set()`, blocking the stdio server acceptably).
- **E3 Tests** — matrix coverage (immediate-match / timeout / other-type / wakes-on-new; limit+since composition; from_ filter; reconcile tail spy), fixture isolation, flakiness of the threaded wait test.
- **E4 Correctness — reconcile tail** — verify the "session.json backstop ⇒ no double-spawn" argument for the generous tail; confirm 2000 is safe; confirm aged-out error re-log is the only downside.
- **E5 Token-efficiency premise** — does the preamble + tools actually remove the S10 waste patterns (shell-watchers, redundant verification, unbounded reads, verbose recaps) the spec targets?
