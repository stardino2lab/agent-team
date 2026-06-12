# Progress

## Current: S8 on main — Next: S9 real teammates

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

## S8 plan review @ 2026-06-12

- `docs/s8-api-sketch.md` 신규 — 5인 전문가 plan 리뷰: D1~D15 결정 lock-in
- 핵심 결정: watchfiles 트리거(polling 폐기), `TeammateRunner(mock)` 패턴, `--dry-run`/`--no-psmux` orthogonal, `teammate_ready`/`session_started` 이벤트, 8 test slot

## S8 implementation @ 2026-06-13

- `teammate_runner.py` 신규 — `PersonaRegistry.spawn_prompt_template` 렌더 + `PsmuxBackend.split_pane/send_keys`. `mock=True`는 dry-run 안전 명령 + `send_keys` 생략
- `orchestrator.py` 신규 — `run_once()` 멱등, `reconcile_handled()` 재시작 안전, `start()`/`attach()` lifecycle, `max_teammates` 캡 재검증(`error` event)
- `_watcher.py` 신규 — s7 `SessionWatcher`를 일반 `FileWatcher`로 추출(`recursive`·`label` 파라미터). `tui/watcher.py`는 thin wrapper로 유지(s7 회귀 0)
- `cli/start.py`, `cli/attach.py` 신규 — `--dry-run`/`--no-psmux`/`--no-block`(테스트 시임). `__main__.py` 등록
- `tui/loaders.format_event_summary` — `session_started`, `teammate_ready`, `error` case 추가
- 신규 14 테스트(4 runner + 8 orchestrator + 3 CLI + 새 loaders case + watcher 통합)
- **163 passed**(+14), 1 skipped, ruff clean

## Next action

1. S9 plan gate → real teammate processes (`TeammateRunner(mock=False)` end-to-end + handshake)

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
| S8 | done |
| S9 | pending |
| S10 | pending |
