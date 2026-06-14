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

## CLI registry seam @ 2026-06-13

- Plan: `~/.claude/plans/claude-inherited-nebula.md` (5-expert review, scope reduced to data-only registry).
- `src/agent_team/cli_registry.py` 신규 (leaf module, no agent_team transitive imports): `CliSpec(frozen)` + `__post_init__` invariant + `_REGISTRY` (`claude` lead+teammate, `codex` teammate-only) + lookup 3개 (`get_cli_spec` / `is_lead_supported` / `is_teammate_supported`) + 예외 2개 (`UnknownCliError` / `LeadCliNotSupportedError`).
- enum 3곳을 registry lookup으로 교체: `personas.py:43`, `spawn_approval.py::_VALID_CLI` 삭제 후 `_validate_request_fields`, `orchestrator._check_lead_cli_supported` (was `_SUPPORTED_LEAD_CLIS` frozenset). 메시지 substring (`"Invalid cli"`, S11 hint) 모두 보존.
- `orchestrator._build_lead_launch_command` 의 `NotImplementedError` → `LeadCliNotSupportedError` (동일 메시지 substring, 동일 raise 시점).
- antigravity 는 registry 에 **등록하지 않음** — S11 PR에서 persona YAML + entry + lead launch builder 같이.
- `_write_lead_mcp_config` 시그니처/내용 무변경(`claude-mcp.json` 그대로). S11에서 `spec.mcp_config_filename` 으로 파라미터화.
- 테스트 신규/보강: `test_cli_registry.py` 11건 (parametrize invariant + lookup + post_init), `test_orchestrator.py` substring 분해 검증 + lead unsupported parametrize 3 케이스 (codex/antigravity/xyz) + cleanup, `test_personas.py` / `test_spawn_approval.py` antigravity/xyz reject 메시지 호환, `test_teammate_runner.py` parametrize `(claude, codex)`.
- 문서: `tests/manual/s9-claude-lead.md:80` `NotImplementedError` → `LeadCliNotSupportedError`. `IMPLEMENTATION.md` §Schemas members.cli registry 주석 + bundled mirror 동기화 정책 한 줄. `s9-api-sketch.md` D11 cell + 테스트 슬롯 #7 갱신.

## S9 manual smoke + code review (2026-06-14)

Ran `tests/manual/s9-claude-lead.md` against psmux (tmux 3.3.5 Win port) + claude
2.1.175. Core flow verified end-to-end: lead claude launched with `--strict-mcp-config`
isolation, `list_personas`/`spawn_teammate` over MCP, TUI approval, teammate pane +
rendered AGENTS.md, audit trail `session_started → spawn_requested → spawn_approved →
teammate_ready`. The smoke + a high-effort code review surfaced and fixed real bugs:

- send_keys typed a literal "Enter" (`-l <keys> Enter`) → lead launch never executed → Enter is now a separate send-keys call.
- bare `claude` mis-resolved to a non-existent `claude.exe` in the pwsh lead pane → resolve via `shutil.which` (full `.CMD` path). Lead stays `new_session` shell + send_keys: the pane anchors the session, and a direct `command=` launch kills the session when claude exits (verified empirically).
- TUI header teammate count frozen at `on_mount` (0/3) → recomputed in `refresh_all_panels`.
- `start` leaked `LeadCliNotSupportedError`/`SessionExistsError` as raw tracebacks → caught → clean message.
- `write_json` non-atomic → TUI refresh could read a half-written `session.json` → temp + `os.replace`.
- MCP config used bare `"python"` → `sys.executable`; filename now from `cli_registry.mcp_config_filename`; team panel no longer double-loads the session per refresh.

## Next action

1. S9 done (manual smoke passed with fixes) → S10 (payment-api E2E) 진입.
2. S11 PR — codex/antigravity 실제 lead launch builder + persona YAML + registry entry 추가.

### Carried into S9+ from earlier reviews

- ✅ ~~Lead pane bootstrap~~ — S9 code-complete 에서 처리. CLI registry seam PR이 enum 추상화까지 마무리.
- ✅ ~~teammate_ready handshake~~ — done in S10b: teammate writes a ready marker via `agent-team teammate ready`; orchestrator `poll_ready` (teammates-dir watcher) emits teammate_ready only then.
- ✅ ~~Teammate prompt newlines (review #5)~~ — fixed in S10a: single-line kickoff via `_kickoff_line`; full role/task context lives in the brief file.
- ✅ ~~Teammate cwd (review #7)~~ — fixed in S10a: teammate pane cwd is the project root; brief stays in the session scratch dir (no pollution).
- **EventLog tail-by-type API**: `Orchestrator.reconcile_handled` reads the full events.jsonl each attach. Bound it once long-running sessions exist.

## S10a — teammate work foundation (2026-06-14)

CLI-neutral fix so a spawned teammate does real work. `TeammateRunner.spawn` now
sets the pane cwd to the project root (#7) and triggers via a single-line "read
your brief" kickoff (#5); launch stays bare `command=persona.cli` (heterogeneous-
team invariant intact). Brief stays in the session scratch dir — no project
pollution. Spec/plan: `docs/superpowers/specs/2026-06-14-s10a-*-design.md`,
`docs/superpowers/plans/2026-06-14-s10a-*.md`.

5-expert code-review gate: 1 BLOCKING fixed (resolve brief path to absolute so a
relative `AGENT_TEAM_HOME` can't hide the brief from the project-cwd teammate) +
test hardening (direct `_kickoff_line` tests, brief-content lock). 208 passed,
ruff clean.

Remaining S10 slices: S10d manual E2E.

### S10c — payment-api fixture + codex teammate (2026-06-15)

Added `tests/fixtures/payment-api/` (the S10d E2E project): config with the 4
team personas, TEAM.md, a minimal `PaymentService` + passing tests (the pattern
the team extends for refunds), the new-feature playbook, and a standalone
pyproject so a teammate can run `pytest tests/ -q` there. Codex teammates use the
same CLI-neutral launch (no per-CLI code); a test spawns the codex implementer
against the fixture and asserts a bare `codex` command with no flags. Root
pyproject ignores `tests/fixtures` for pytest + ruff. 3-expert review: 0 BLOCKING
(verification deepened with the codex-spawn test). 216 passed, ruff clean.

### S10b — real teammate_ready handshake (2026-06-15)

Marker-file handshake: teammate runs `agent-team teammate ready` → orchestrator
`poll_ready` (teammates-dir watcher, RLock-serialized with the approval watcher)
emits `teammate_ready` only when the marker appears. `Member` gains `request_id`
(persisted); status goes `starting → running`; `reconcile_handled` treats a
member's request_id as the authoritative "already spawned" signal so a
detach/attach before readiness never re-spawns. No new event type, no blocking
wait, no timeout (deferred). Spec: `docs/superpowers/specs/2026-06-15-s10b-*`.

5-expert code-review gate: 1 BLOCKING fixed (lock `reconcile_handled`'s mutation
of the shared handled set) + 1 P1 (independent per-watcher start guards). 212
passed, ruff clean.

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
| S9 | done (manual smoke passed 2026-06-14) |
| S10 | in progress (S10a done 2026-06-14) |
