# Progress

## Current: S7 on main — Next: S8 orchestrator

## Last completed: S6 @ 2026-06-10

- `mcp_server.py` — 9 MCP tools; on main

## S7 plan review @ 2026-06-10

- `docs/s7-api-sketch.md` — Textual 2×2, watchfiles, spawn modal
- 6-expert plan review: BLOCKING=0
- Post-review: dual entry (`--session` + `AGENT_TEAM_SESSION_ID`), `handle_approve/deny`, 11 tests, `__main__.py` contract

## S7 implementation @ 2026-06-10

- `tui/` — Textual 2×2, watchfiles, spawn modal, dual entry
- `cli/tui_cmd.py` — `agent-team tui`
- 11 TUI tests; **134 passed**, 1 skipped
- Fix: `log_panel` (avoid Textual `App.log` clash)

## S7 hardening (5-expert review) @ 2026-06-12

- watcher: `awatch` (async) → `watch` (sync) — real watcher was crashing on first event; all prior tests masked it with `MagicMock`
- watcher: try/except on loop + callback; rate-limit debounce (no trailing-edge drop) cancelable via `_stop.wait`
- modal: `check_spawn_modal` idempotent by `request_id`; removed double-pop in `_resolve`; explicit escape no-op binding
- loaders: `json.JSONDecodeError` guard in `load_mail_rows`; `.get()` consistency in `format_event_summary`
- tests: real-watchfiles integration (`test_watcher.py`), pilot 4-panel + Y/N + F5 + modal-stays-open, malformed JSONL + missing-payload cases, context error paths; **144 passed**, 1 skipped

## S0~S6 expert review (23-expert, Part 1+2) @ 2026-06-12

- Code gate: **BLOCKING=0**, P1=13 (5 immediate / 3 → S8 / 2 docs / 3 misc)
- Plan: `~/.claude/plans/expert-review-temporal-deer.md`
- S8-safe patches applied:
  - `tasks.py::list_tasks` 숫자 정렬 (사전식 정렬 → `_TASK_ID_PATTERN` 기반 int key)
  - `cli/logs.py::tail_cmd` `json.dumps(payload, default=str)`
  - `mcp_server.py::_map_tool_error` `JSONDecodeError` → "malformed session data"
  - `tests/unit/test_session.py::test_load_missing_raises` 신규 1건
- Verify: pytest **149 passed**, 1 skipped; ruff clean
- 보류 (S8 완료 후 별도 PR, 6건): session.py `load` wrap / `default_base_dir` 빈 문자열 / `project_loader.build_lead_context` 사용자 키 노출 / `_io._load_yaml_dict` 통합 (personas+project_loader) / IMPLEMENTATION.md doc drift × 2 (pending.json 필드, jinja2 마일스톤)
- S8 작업자 정보 제공 (3건): missing events `session_started`/`teammate_ready`/`error` emit, `spawn_teammate` ready 콜백 메커니즘, `max_teammates` cap 재검증 in spawn dispatch

## Next action

1. S8 plan gate → implement orchestrator + pane spawn

## Blockers

- none

## Milestone gates

| ID | Status |
|----|--------|
| P0 | done |
| P0.5 | done |
| P0.6 | done |
| S0 | done |
| S1 | done |
| S2 | done |
| S3 | done |
| S4 | done |
| S5 | done |
| S6 | done |
| S7 | done |
| S8 | pending |
| S9 | pending |
| S10 | pending |
