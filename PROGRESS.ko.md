# 진행 상황

## 현재: S13~S18 로드맵 전체 코드 완료 @ 2026-06-21 — 411 passed/1 skipped, ruff clean. 남은 건 라이브 게이트(아래) + 소비자-부재 연기(S15b, S16c/d/e). main 머지 미실시(브랜치 s15~s18).

## 최근 완료: G1+Gs 라이브 실행 + Ubuntu(claude+codex) 준비 push @ 2026-06-22

> 영문 소스(상세·커밋 단위): [PROGRESS.md](PROGRESS.md). 본 문서는 그 한글 미러.

## 라이브 게이트 인덱스 (코드는 전부 단위테스트됨 — 토큰/Linux/헤드리스 검증만 잔여)

| 게이트 | 파일 | 검증 대상 | 상태 |
|---|---|---|---|
| G5 헤드리스 E2E (캡스톤) | `tests/manual/s18c-headless.md` | 무인 자율: start→외부승인→작업→종료→`final` 매니페스트, timeout/stop/SIGTERM/crash 변형, 헤드리스 Linux | 대기 |
| S18b 데몬 수명주기 | `tests/manual/s18b-daemon-lifecycle.md` | graceful stop/exit-code, `--timeout` kill-all, `final`/terminal status, SIGTERM graceful, crash→stop 리퍼 | 대기 |
| S18a 외부 승인자 | `tests/manual/s18a-external-approver.md` | Hermes approve/deny, TUI 안 열림, `decided_by:hermes` | 대기 |
| S17 worktree 격리 (G6) | `tests/manual/s17-worktree-gates.md` | 두 writer 같은 파일 격리/머지/prune, Windows 경로길이·락 | 대기 |
| S14 status 게이트 (Gs) | `tests/manual/s14-status-gates.md` | 실제 dead-pane, transcript mtime 전진 | free+dead-detect **PASS**(Win) · **mtime-falsepos FAIL**(Win) |
| S13c tmux Linux (G3/G4) | `tests/manual/s13-tmux-linux.md`, `ubuntu-attended-runbook.md` | Linux tmux 멀티페인/kickoff/dead-detect (tmux≥3.4) + claude lead+codex 티미 | 대기 (런부크 준비됨) |
| S15a/S12 agy 토큰 (G1) | `tests/manual/s12-agy-gates.md` | agy 티미 라이브: kickoff, auto-approve, helper-under-agy | G0 PASS · G1 부분 PASS(Win), 자동 kickoff **cold=FAIL(drop)**/warm=OK |

**연기 (소비자 없어서):** S15b agy-LEAD (agy `mcp` 서브커맨드 부재 → MCP 호스팅 스파이크 필요), S16c/d/e (실제 Hermes 생겨야 매니페스트/triage 스키마 동결).

**G1 라이브 발견 @ 2026-06-21 (Windows, 한글 로케일):** agy 티미 능력 자체 PASS(hello.txt 생성). 버그 2개 —
- **[FIXED] cp949 디코드 크래시** (`psmux_backend._run`): `subprocess.run(text=True)` 인코딩 미지정 → cp949로 psmux 박스문자 디코드 → `UnicodeDecodeError` → 크래시. `encoding="utf-8", errors="replace"` 로 수정.
- **[OPEN] agy cold-boot kickoff drop** (`teammate_runner._wait_until_input_ready`): "출력 안정=입력준비" 휴리스틱이 agy 정적 splash에 ~0.5초만에 settle → 컴포저 준비 전 send_keys → 키 유실 (cold 재현/warm 우연성공 = 레이스). **G5 자율의 전제.** agy 실사용 시점 수정.

## 다음 액션

1. **라이브 게이트 실행** — 위 인덱스(특히 G5 헤드리스 캡스톤, S13c Linux tmux, agy cold-boot 수정).
2. **연기 항목** — agy-LEAD MCP 호스팅 스파이크(S15b), Hermes 소비자 생기면 S16c/d/e 스키마 동결.
3. **main 머지** — s15~s18 브랜치 라이브 게이트 통과 후.

상세 결정·검증은 [PROGRESS.md](PROGRESS.md) · [docs/s13-next-phase-roadmap.md](docs/s13-next-phase-roadmap.md) · [docs/s11-multi-cli-plan.md](docs/s11-multi-cli-plan.md) 참조.

## 블로커

- 없음 (코드 차단 0; 라이브 게이트는 사용자 토큰/환경 필요라 "대기"이지 블로커 아님)

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
| S11 | a/b code-complete + 라이브 e2e @06-20: claude-lead + codex/agy-teammate **PASS**(Win). **S11c codex-LEAD FAIL** (codex exec가 agent-team MCP 미로드). 상세 `tests/manual/s11b-*`, `s11c-*` |
| S12 | S12a agy/Antigravity 팀원 code-complete @06-19, G0 PASS — G1 토큰 게이트 부분/잔여; 리드 보류(MCP 스파이크). `tests/manual/s12-agy-gates.md` |
| S13 | code-complete — TerminalBackend 추상화 + TmuxBackend(Linux/macOS) + 팩토리. Linux tmux 라이브 게이트 대기 |
| S14 | code-complete — health 모델 + `agent-team status` + escalation 도출 + bounded spawn retry |
| S15 | S15c code-complete — cost-aware 역할→CLI override + agy-tester persona. (S15b agy-LEAD 연기) |
| S16 | S16a/b code-complete — 읽기전용 결과 매니페스트 투영 + 세션종료 캐시. (S16c/d/e 연기) |
| S17 | code-complete — git worktree 격리(봉쇄). worktree 라이브 게이트(G6) 대기 |
| S18 | a/b/c code-complete — 외부 승인자 CLI + 데몬 수명주기 + 헤드리스 E2E 체크리스트(G5). 라이브 게이트 대기 |

---

## 완료 이력 (아카이브)

> S11~S18 슬라이스 요약. 커밋 단위 상세는 영문 [PROGRESS.md](PROGRESS.md) 해당 섹션 참조.

### S15c~S18 — 자율운영 기반 (2026-06-21, 브랜치 s15~s18)

per-step 전문가 리뷰가 구현 전 BLOCKING 차단. 332→411 테스트, 단계별 커밋.

- **S15c [2ca2442]** cost-aware 역할→CLI: `role_cli_overrides`(persona명 키, `is_teammate_supported` 검증) + `agy-tester` persona. 리뷰 BLOCKING: override가 기록만 바꾸고 런치는 persona 기본 CLI 재유도 → 승인 cli를 `_spawn_one`→`teammate_runner.spawn(cli=)`로 관통.
- **S16a/b [79e01e5]** Hermes 결과 매니페스트: 신규 `manifest.py` 순수 투영(`build_manifest`) + `logs manifest` CLI(json/jsonl/md) + 세션종료 `result_manifest.json` 캐시. **두 번째 진실원본 없음** — 기존 store read-time 투영. (S16c/d/e 연기)
- **S17 [dcf4fb2]** worktree 격리(봉쇄): `isolate_worktrees` 플래그 + `workspace-write` persona만 자기 `git worktree`에서 실행. spawn시 생성(멱등/고아 자가치유), shutdown시 prune. 생성 실패=하드스톱(공유 폴백 금지).
- **S18a [e17bae6]** 외부 승인자 CLI `approvals`(list/approve/deny) — Hermes가 TUI 없이 spawn 승인, spawn 게이트 불변. `SpawnRequestNotFoundError`→`CLI_ERRORS`.
- **S18b1 [f38f070]** graceful `stop` + 공유 `block_until_stopped`(stop 마커 폴링, 종료코드). 이벤트→마커 순서(매니페스트 race 방지), 시작시 stale 마커 클리어.
- **S18b2 [893b1b2]** `--timeout`/`--autonomous`(autonomous는 timeout 필수) + 종료시 kill-all-panes + 매니페스트 `final` 불린/terminal `session_status`. **Hermes는 `final=true`에만 반응.** MANIFEST_VERSION 2.
- **S18b3 [351a50d]** SIGTERM graceful 종료 매니페스트(컨테이너/`kill` → 클린 매니페스트, 헤드리스 Linux 의미) + `stop` 고아 pane 리퍼.
- **S18c [b738b33]** 헤드리스 자율 E2E 게이트 체크리스트(G5) — 코드 없음.

### S13~S14 — 백엔드 추상화 + 헬스 (2026-06)

- **S13a/b** `TerminalBackend` 추상화 + 팩토리(Windows 동작보존) → `TmuxBackend`(Linux/macOS, tmux≥3.4). 단일 백엔드 인터페이스 뒤에서 OS별 분기.
- **S14a~d** health 모델 + `agent-team status`(읽기전용 스냅샷, dead-pane/transcript mtime) + escalation 도출 표면화 + bounded spawn 재시도(backoff 타이머) + `event_log.read` 찢어진 trailing line 내성.

### S11 — 멀티-CLI 리드/팀원 하드닝 (2026-06-15 ~ 06-20)

- **S11a ($20-lead 하드닝):** `LEAD_ORCHESTRATION_PREAMBLE`(orchestrate-only 구조적 잠금) + MCP 2 tool 추가(`get_recent_events`/`wait_for_event`, watchfiles 이벤트 구동 → 리드가 폴링 없이 1회 blocking, 토큰 0). **MCP tool 9→11.** D9 bounded/filtered reads(`EventLog.read(limit=)`, `from_` 발신자 필터, reconcile tail 2000).
- **S11b (관측/신뢰성):** registry `teammate_launch_args`(codex `--dangerously-bypass-approvals-and-sandbox`) + `capture_pane`/`pipe_pane`(팀원 transcript→디스크, 리드 컨텍스트 0) + `_wait_until_input_ready`(CLI-중립 kickoff 입력준비 대기) + `logs export --to <dir>` 번들.
- **S11c (codex 2nd lead):** registry `mcp_format`(json/toml) + `_write_lead_mcp_config` 포맷 디스패치(codex CODEX_HOME 프로필 TOML) + `_build_lead_launch_command` codex 분기(`codex exec --profile ...`). `lead_cli` config로 리드 플립(비용 다이얼).
- **라이브 e2e(Win, 실 CLI):** claude 리드 + codex 팀원 **PASS**(submit=Enter on Win). **codex-as-lead FAIL** — codex가 agent-team MCP 미로드(profile overlay에서 `mcp_servers` 미적재 추정). claude가 유일 동작 리드. 2 블로커(codex update-nag, codex-lead MCP) → 후속.

### S12 — agy(Antigravity) 팀원 (2026-06-19, gemini 치환)

- gemini S12a 슬라이스(registry + `gemini-*` persona + 6 테스트)는 **agy로 대체**(제거, 병존 아님). agy는 Claude-Code 파생(v1.0.10).
- registry `agy` `CliSpec`: `supports_teammate=True`, `supports_lead=False`(MCP 서브커맨드 부재 → 리드 연기), `teammate_launch_args=("--dangerously-skip-permissions",)`(단일 auto-approve 플래그). INTERACTIVE(pane+send_keys kickoff), `-p`/`--print` 아님.
- `agy-implementer`/`agy-planner` persona(bundled↔root 미러), **opt-in**(`allowed_personas` 추가 필요 — 기존 claude/codex 팀 무영향).
- 라이브 게이트: G0(무토큰) **PASS**, G1+helper 토큰 게이트 잔여. 설계: `docs/superpowers/specs/2026-06-19-s12a-agy-teammate-design.md`.

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
