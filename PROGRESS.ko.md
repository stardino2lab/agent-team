# 진행 상황

## 현재: S10 완료 — 다음: S11 (멀티-CLI + $20-lead 토큰/관측 하드닝)

## 최근 완료: S10 payment-api 실토큰 E2E @ 2026-06-15 — 통과

- 이기종 팀 — planner(claude) → implementer(codex) → tester(codex) → reviewer(claude),
  claude/Opus 리드가 오케스트레이션 — 이 `PaymentService.refund` + 테스트를 빌드,
  `pytest tests/ -q` → **4 passed**, reviewer APPROVED
- 실제 핸드셰이크 동작(팀원이 `agent-team teammate ready` 실행한 뒤에만 `teammate_ready`)
- mail + 태스크 보드 + shutdown 모두 동작, events.jsonl 전체 audit trail
- 전체 **216 passed**, ruff clean

## 다음 액션

1. **S11a — $20-lead 하드닝 (최우선):** D6 orchestration-only preamble + D8 event-driven wait(폴링 제거) + D9 bounded/filtered reads
2. **S11b — 관측/신뢰성:** D10 팀원 transcript 캡처 + D11 kickoff input-readiness + D12 codex 팀원 비대화형 launch
3. **S11c — codex 2nd lead:** D1/D2(per-CLI dispatch + JSON/TOML 렌더러) + D3 + D4(config 기반 역할 배정)
4. **S12 (병렬 spike):** Gemini/Antigravity 설치 + G0–G6 검증 → 팀원(S12a) → 리드(S12b)

상세 결정·검증은 [docs/s11-multi-cli-plan.md](docs/s11-multi-cli-plan.md) 참조.

## 블로커

- 없음

## 마일스톤 게이트

| ID | 상태 |
|----|------|
| P0 | 완료 |
| P0.5 | 완료 |
| P0.6 | 완료 |
| S0 | 완료 |
| S1 | 완료 |
| S2 | 완료 |
| S3 | 완료 |
| S4 | 완료 |
| S5 | 완료 |
| S6 | 완료 |
| S7 | 완료 |
| S8 | 완료 |
| S9 | 완료 (수동 스모크 통과 2026-06-14) |
| S10 | 완료 (실토큰 E2E 통과 2026-06-15) |
| S11 | 예정 |
| S12 | 예정 |

---

## 완료 이력 (아카이브)

### S10 — payment-api E2E (2026-06-14 ~ 06-15)

- **S10a — 팀원 작업 기반:** `TeammateRunner.spawn` 이 팀원 pane cwd 를 프로젝트 루트로 설정(#7),
  단일 라인 "read your brief" kickoff 로 트리거(#5). launch 는 bare `command=persona.cli` 유지(이기종 팀 불변식).
  brief 는 세션 scratch 디렉터리에 — 프로젝트 오염 없음. 5인 리뷰: 1 BLOCKING 수정(brief 절대경로 resolve). 208 passed.
- **S10b — 실제 `teammate_ready` 핸드셰이크:** 팀원이 `agent-team teammate ready` 실행 → 오케스트레이터
  `poll_ready`(teammates-dir watcher, approval watcher 와 RLock 직렬화)가 marker 등장 시에만 `teammate_ready` emit.
  `Member.request_id` 추가(영속), status `starting → running`. 5인 리뷰: 1 BLOCKING + 1 P1 수정. 212 passed.
- **S10c — payment-api fixture + codex 팀원:** `tests/fixtures/payment-api/`(4 페르소나 config, TEAM.md,
  최소 `PaymentService`+테스트, new-feature 플레이북, standalone pyproject). codex 팀원도 CLI-neutral launch.
  루트 pyproject 가 `tests/fixtures` 를 pytest/ruff 에서 제외. 3인 리뷰: 0 BLOCKING. 216 passed.
- **S10d — 수동 E2E 게이트 통과(2026-06-15):** 위 "최근 완료" 참조.
  - 후속 발견(S11 로 폴딩): 팀원 kickoff 타이밍(CLI input-ready 전 send_keys → D11), codex 작업 visibility(transcript → D10),
    병렬화는 kickoff 수정 후. codex 팀원 per-command 승인 차단 → D12.
- 설계/계획: `docs/superpowers/specs/2026-06-14-s10a-*`, `2026-06-15-s10b-*`, `docs/superpowers/plans/2026-06-14-s10a-*`

### S9 — Claude 리드 통합 (2026-06-13 ~ 06-14)

- `bundled_paths.render_bundled_template`(Jinja PackageLoader 단일 진입),
  `orchestrator._write_lead_mcp_config`(`{session_dir}/claude-mcp.json`),
  `orchestrator._build_lead_launch_command`(claude 분기 + codex/antigravity는 S11+)
- `Orchestrator.start` — MCP config 쓰기 → lead pane `send_keys(claude --mcp-config ... --strict-mcp-config --append-system-prompt ...)`,
  `config.yaml.lead_cli`(default claude) 로 lead CLI 결정
- `TeammateRunner.spawn` — `{session_dir}/teammates/{name}/AGENTS.md` 렌더 + 그 디렉터리에서 split
- **CLI registry seam:** `cli_registry.py`(데이터 전용, `CliSpec` + `claude`/`codex` 등록 + lookup/예외).
  enum 3곳을 registry lookup 으로 교체. antigravity 는 S11 까지 미등록
- **수동 스모크(2026-06-14):** psmux(tmux 3.3.5 Win port) + claude 2.1.175 로 end-to-end 검증.
  스모크 + high-effort 코드 리뷰가 실버그 수정: 리터럴 "Enter" 전송, bare `claude` 미해결(→ `shutil.which`),
  TUI 헤더 카운트 freeze, `start` raw traceback, non-atomic `write_json`, bare `"python"`(→ `sys.executable`)
- **177 passed** → registry seam 후 정착. 상세: [docs/s9-api-sketch.md](docs/s9-api-sketch.md)

### S8 — 오케스트레이터 dry-run (2026-06-13)

- `teammate_runner.py`(persona spawn 템플릿 렌더 + psmux split/send; `mock=True` dry-run 안전),
  `orchestrator.py`(`run_once()` 멱등, `reconcile_handled()` 재시작 안전, lifecycle, max_teammates 캡 재검증),
  `_watcher.py`(s7 SessionWatcher 를 일반 `FileWatcher` 로 추출), `cli/start.py`/`cli/attach.py`(`--dry-run`/`--no-psmux`/`--no-block`)
- **163 passed**(+14). 상세: [docs/s8-api-sketch.md](docs/s8-api-sketch.md)
- 부속: S0~S6 23인 전문가 리뷰(BLOCKING=0) + 보류 6건 적용 + secret 누출 revert(3키 allowlist 복원)

### S7 — Textual TUI (2026-06-10, 하드닝 2026-06-12)

- 기능: mail/task/team/log 현황 + spawn 승인 모달 (Textual pane 내부 오버레이)
- 모듈: `tui/`, `cli/tui_cmd.py`, `agent-team tui`
- 하드닝(5인 리뷰): 동기 watcher 전환(`awatch`→`watch` 크래시 수정), 모달 멱등, 로더 가드
- 상세: [docs/s7-api-sketch.md](docs/s7-api-sketch.md) · [docs/blueprints/s7-tui.html](docs/blueprints/s7-tui.html)

### S6 — MCP 서버 (2026-06-10)

- 기능: 팀 리드용 MCP 9 tools (spawn, mail, task, shutdown 등)
- 모듈: `mcp_server.py`
- 상세: [docs/s6-api-sketch.md](docs/s6-api-sketch.md)

### S5 — Spawn 승인 큐 (2026-06-10)

- 기능: 팀원 spawn 요청 저장 → 승인/거부 → `resolutions.jsonl` 기록
- 모듈: `spawn_approval.py`, `approval/pending.json`, `approval/resolutions.jsonl`
- 상세: [docs/s5-api-sketch.md](docs/s5-api-sketch.md)

### S4 — psmux 백엔드 (2026-06-10)

- 기능: psmux 세션 생성, pane 분할, 키 전송, pane 종료·목록 (mock + integration)
- 모듈: `psmux_backend.py`
- 상세: [docs/s4-api-sketch.md](docs/s4-api-sketch.md)

### S3 — CLI 코어 (2026-06-10)

- 기능: `agent-team mail send|read`, `task create|list|claim|complete`, `logs tail|export`, `personas list`, `context show`
- 모듈: `cli/mail.py`, `task.py`, `logs.py`, `personas_cmd.py`, `context.py`
- 상세: [docs/s3-api-sketch.md](docs/s3-api-sketch.md)

### S2 — 페르소나 + 프로젝트 로더 (2026-06-10)

- 기능: `agent-team init` — 소비자 repo에 `.agent-team/`, `TEAM.md` 스캐폴드; 페르소나 YAML 로드
- 모듈: `personas.py`, `project_loader.py`, `cli/init.py`, `personas/*.yaml`
- 상세: [docs/s2-api-sketch.md](docs/s2-api-sketch.md)

### S1 — 코어 데이터 레이어 (2026-06-10)

- 기능: 세션 디렉터리, 메일박스(JSONL), 태스크 보드, append-only 이벤트 로그
- 모듈: `session.py`, `mailbox.py`, `tasks.py`, `event_log.py`, `_io.py`
- 상세: [docs/s1-api-sketch.md](docs/s1-api-sketch.md)

### S0 — 스캐폴드 (2026-06-10)

- 기능: `pip install -e .`, `pytest`, `agent-team` CLI 진입점
- 파일: `pyproject.toml`, `src/agent_team/`, `tests/conftest.py`
- 상세: [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) §S0

### P0.5 — 보조 스펙 (2026-06-10)

- 산출물: 스키마, MCP, 플레이북, 페르소나 템플릿, S9/S10 수동 테스트 문서
- 상세: [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) §P0.5

### P0 — 초기 문서 (2026-06-10)

- 산출물: PRD, RGIO, AGENTS.md, IMPLEMENTATION, PROGRESS, README
- 상세: [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) §P0
