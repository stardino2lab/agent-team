# Progress

## Current: S9 code-complete on main — Next: S9 manual smoke + S10

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

## S0~S6 expert review follow-up (보류 6건 적용) @ 2026-06-13

- Plan: `~/.claude/plans/expert-review-temporal-deer.md` Part 5
- 그룹 A (3 patches, S8 호출 영향 LOW):
  - `session.py::default_base_dir` 빈 문자열/whitespace 거절 (`if home and home.strip()`)
  - `session.py::SessionStore.load` 손상 JSON wrap → `SessionLoadError(ValueError)` 신규
  - `project_loader.py::build_lead_context` 사용자 정의 config 키 노출 (`yaml.safe_dump(config)` 전체 dump)
- 그룹 B (atomic 리팩터링): `_io.load_yaml_dict(text, label, error_cls)` 공개 추출 → `personas.py` + `project_loader.py` 로컬 중복 제거. exception type(`PersonaLoadError`/`ProjectConfigError`/`PlaybookLoadError`) 보존.
- 그룹 C (문서): `IMPLEMENTATION.md` §Schemas pending.json 예시에 `prompt`+`teammate_name` 필드 추가, §Dependencies 표에서 jinja2를 S8 → S2(실제 init 사용 시점)로 정정
- 신규 회귀 테스트 2건: `test_load_corrupt_raises` (SessionLoadError), `test_build_lead_context_emits_custom_keys`
- Verify: pytest **169 passed**, 1 skipped, ruff clean
- S8 정보 제공 3건 회고: E(누락 이벤트)·G(cap 재검증) S8에서 처리 완료, F(spawn_teammate ready 콜백) teammate_ready 이벤트로 부분 처리

## S0~S6 follow-up code review (3-expert) @ 2026-06-13

- 3-expert code review on `77c7023`: BLOCKING=1(=P1 재평가), P1=1, P2=6 — 핵심은 `build_lead_context` 전체 dump가 secret 누출 default unsafe
- 결정: **옵션 3 (A-3 revert)** — 3키 allowlist(`max_teammates`/`playbook_mode`/`allowed_personas`) 복원. 사용자 도메인 컨텍스트 전달은 TEAM.md / `--context "..."` 정식 경로 사용.
- Revert: `project_loader.py::build_lead_context` 원복. 테스트도 누출 검증으로 교체(`test_build_lead_context_does_not_leak_unknown_keys`).
- 문서: `IMPLEMENTATION.md` §Schemas config.yaml 항목에 "Lead exposure scope" 명시 (allowlist 의도 + TEAM.md/--context 경로 안내)
- Verify: pytest **172 passed**, 1 skipped, ruff clean

## S9 plan review @ 2026-06-13

- `docs/s9-api-sketch.md` 작성 + 5인 전문가 plan 리뷰 (D1~D11)
- Q1·Q2·Q3 사용자 환경에서 확인 — `--mcp-config`, `--strict-mcp-config`, `--append-system-prompt` 모두 존재 (Claude 2.1.175)
- 다중 CLI 입장 (D11) = B 경량 isolation (사용자 결정) — `_build_lead_launch_command` + `lead_cli` config field

## S9 code-complete @ 2026-06-13

- `agent_team.bundled_paths.render_bundled_template` 신규 — Jinja `PackageLoader` 단일 진입
- `agent_team.orchestrator._write_lead_mcp_config` 신규 — `{session_dir}/claude-mcp.json` 렌더 (json.dumps; Windows backslash 안전)
- `agent_team.orchestrator._build_lead_launch_command` 신규 — claude 분기 + codex/antigravity NotImplementedError (S11+)
- `Orchestrator.start` — MCP config 쓰기 → lead pane `send_keys(claude --mcp-config ... --strict-mcp-config --append-system-prompt ...)` → split TUI pane
- `Orchestrator.start` — `config.yaml.lead_cli` (default `claude`) 로 lead `cli` 결정
- `TeammateRunner.spawn` — `{session_dir}/teammates/{name}/AGENTS.md` 렌더 + 그 디렉터리에서 split_pane (AGENTS.md 자동 인지)
- 템플릿 이동: `templates/teammate/AGENTS.md.codex.j2` → `src/agent_team/bundled/templates/teammate/AGENTS.md.j2`. `templates/claude-mcp.json.example` 은 reference 로 루트 유지 (json.dumps 가 더 안전해서 템플릿 미사용)
- `bundled/templates/project/config.yaml.j2` + 루트 동기본 — `lead_cli: claude` 기본값 추가
- `tests/fixtures/minimal-project/` 신규 — `.agent-team/config.yaml` + `TEAM.md`
- 신규 6 테스트 (4 unit + 1 e2e + 1 NotImplementedError + AGENTS.md 슬롯 보강)
- **177 passed**(+5), 1 skipped, ruff clean

## Next action

1. **S9 manual smoke** — `tests/manual/s9-claude-lead.md` 정정판 사용. psmux + claude 2.1.175 로 한 사이클.
2. 결과 pass 면 S9 done → S10 (payment-api E2E) 진입.

### Carried into S9 from S8 reviews

- **Lead pane bootstrap**: `orchestrator.start` opens lead pane via `psmux.new_session` but never `send_keys` the `claude`/`codex` launch command, and never injects `project_loader.build_lead_context(playbook, extra_context)`. In S8 dry-run that is a noop; in S9 the lead must actually run with MCP config + TEAM.md context.
- **teammate_ready handshake**: currently emitted right after `send_keys`. S9 should wait for a real ready marker written by the teammate (per `RGIO.md`) before emitting.
- **EventLog tail-by-type API**: `Orchestrator.reconcile_handled` reads the full events.jsonl each attach. Bound it once long-running sessions exist.

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
| S9 | code-complete (manual pending) |
| S10 | pending |
