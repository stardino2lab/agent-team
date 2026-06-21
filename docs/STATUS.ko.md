# agent-team 구현 현황

**한 줄 요약:** S11~S18 로드맵 전체 코드 완료 @ 2026-06-21 (411 passed/1 skipped) — 라이브 토큰/Linux/헤드리스 게이트 잔여, main 미머지(브랜치 s15~s18)

**시각 현황:** [blueprints/status.html](blueprints/status.html) · **진행 로그:** [PROGRESS.ko.md](../PROGRESS.ko.md) · **영문 소스:** [PROGRESS.md](../PROGRESS.md)

---

## 마일스톤 게이트

| ID | 상태 | 비고 |
|----|------|------|
| P0 | 완료 | 초기 문서 |
| P0.5 | 완료 | 스키마·MCP·플레이북 스펙 |
| P0.6 | 완료 | — |
| S0 | 완료 | 프로젝트 스캐폴드 |
| S1 | 완료 | 코어 데이터 레이어 |
| S2 | 완료 | 페르소나·프로젝트 init |
| S3 | 완료 | CLI (mail/task/logs) |
| S4 | 완료 | psmux 백엔드 |
| S5 | 완료 | Spawn 승인 큐 |
| S6 | 완료 | MCP 서버 |
| S7 | 완료 | Textual TUI |
| S8 | 완료 | 오케스트레이터 dry-run (`start`/`attach`, mock 팀원) |
| S9 | 완료 | Claude 리드 통합 — 수동 스모크 통과 (2026-06-14) |
| S10 | 완료 | payment-api 실토큰 E2E 통과 (2026-06-15) |
| S11 | code-complete | 멀티-CLI: claude-lead+codex/agy-팀원 **PASS**(Win) · **codex-LEAD FAIL**(MCP 미로드) · $20-lead 토큰/관측 하드닝 |
| S12 | code-complete | agy/Antigravity 팀원(S12a), G0 PASS — G1 토큰 게이트 부분/잔여; 리드 보류(MCP 스파이크) |
| S13 | code-complete | TerminalBackend 추상화 + TmuxBackend(Linux/macOS, tmux≥3.4) — Linux 라이브 게이트 대기 |
| S14 | code-complete | health 모델 + `agent-team status` + escalation 도출 + bounded spawn retry |
| S15 | code-complete | S15c cost-aware 역할→CLI override + agy-tester (S15b agy-LEAD 연기) |
| S16 | code-complete | S16a/b 읽기전용 결과 매니페스트 투영 + 세션종료 캐시 (S16c/d/e 연기) |
| S17 | code-complete | git worktree 격리(봉쇄) — worktree 라이브 게이트(G6) 대기 |
| S18 | code-complete | 외부 승인자 CLI + 데몬 수명주기(stop/timeout/SIGTERM/final) + 헤드리스 E2E(G5) |

**테스트:** 411 passed / 1 skipped (`pytest tests/ -q`, 2026-06-22 검증)

---

## 구현된 기능

| 마일스톤 | 상태 | 사용자에게 보이는 기능 | 모듈 / CLI |
|----------|------|------------------------|------------|
| P0–P0.5 | 완료 | 요구사항·아키텍처·에이전트 가이드 문서 | `docs/PRD.md`, `docs/RGIO.md`, `AGENTS.md` |
| S0 | 완료 | `pip install -e .`, `agent-team --help` | `pyproject.toml`, `src/agent_team/` |
| S1 | 완료 | 세션·메일박스·태스크·이벤트 로그 (파일 기반) | `session.py`, `mailbox.py`, `tasks.py`, `event_log.py` |
| S2 | 완료 | `agent-team init` — 소비자 프로젝트에 `.agent-team/` 생성 | `personas.py`, `project_loader.py`, `cli/init.py` |
| S3 | 완료 | `agent-team mail`, `task`, `logs`, `personas`, `context` | `cli/mail.py`, `task.py`, `logs.py` 등 |
| S4 | 완료 | psmux 세션·pane 분할·키 전송 (프로그램 API) | `psmux_backend.py` |
| S5 | 완료 | 팀원 spawn 요청 → 승인/거부 → `resolutions.jsonl` | `spawn_approval.py` |
| S6 | 완료 | 팀 리드용 MCP 9 tools | `mcp_server.py` |
| S7 | 완료 | `agent-team tui` — mail/task/team/log + spawn 승인 모달 | `tui/`, `cli/tui_cmd.py` |
| S8 | 완료 | `agent-team start`/`attach` (`--dry-run`/`--no-psmux`) 전체 사이클 | `orchestrator.py`, `teammate_runner.py`, `cli/start.py`, `cli/attach.py`, `_watcher.py` |
| S9 | 완료 | 실제 Claude 리드 부트스트랩 (MCP config + `--strict-mcp-config` 격리) — 수동 스모크 통과 | `orchestrator._build_lead_launch_command`, `cli_registry.py`, `bundled_paths.py` |
| S10 | 완료 | payment-api 실토큰 E2E: 이기종 팀(claude+codex), 실제 `teammate_ready` 핸드셰이크, 팀원 brief/cwd | `teammate_runner.spawn`, `cli/teammate.py`(ready marker), `tests/fixtures/payment-api/` |
| S11 | code-complete | $20-lead 하드닝(orchestrate-only preamble, event-driven wait, bounded reads) + 팀원 transcript 캡처 + codex 비대화형 launch + codex 2nd lead(라이브 FAIL). **MCP tool 9→11** | `mcp_server.py`, `cli_registry.py`, `orchestrator.py`, [s11-multi-cli-plan.md](s11-multi-cli-plan.md) |
| S12 | code-complete | agy/Antigravity 팀원(opt-in persona) — 리드 보류(MCP 스파이크) | `cli_registry.py`, `personas/agy-*.yaml` |
| S13 | code-complete | OS-중립 백엔드: psmux(Win)/tmux(Linux·macOS) 팩토리 | `terminal_backend.py`, `tmux_backend.py`, `psmux_backend.py` |
| S14 | code-complete | `agent-team status` 헬스 스냅샷(dead-pane/transcript mtime) + escalation + spawn 재시도 | `health.py`, `cli/status.py`, `orchestrator.py` |
| S15 | code-complete | `role_cli_overrides`(역할별 CLI 비용 다이얼) + agy-tester persona | `project_loader.py`, `orchestrator.py` |
| S16 | code-complete | `agent-team logs manifest` 결과 매니페스트(json/jsonl/md) + 세션종료 `result_manifest.json` | `manifest.py`, `cli/logs.py` |
| S17 | code-complete | `isolate_worktrees` — writer persona별 `git worktree` 격리/prune | `worktree.py`, `orchestrator.py` |
| S18 | code-complete | `agent-team approvals`(외부 승인) + `agent-team stop`/`--timeout`/`--autonomous` + `final` 매니페스트 + SIGTERM graceful | `cli/approve.py`, `cli/stop.py`, `orchestrator.py` |

---

## 다음 단계

코드는 S11~S18 전부 완료. 남은 건 **라이브 게이트 실행**(사용자 토큰/환경 필요) + 소비자-부재 연기 항목.

1. **라이브 게이트 (최우선):** G5 헤드리스 자율 E2E(캡스톤), S13c Linux tmux(G3/G4), S17 worktree(G6), agy cold-boot kickoff drop 수정(G5 전제). 인덱스: [PROGRESS.ko.md](../PROGRESS.ko.md) · [tests/manual/LIVE-GATES.md](../tests/manual/LIVE-GATES.md).
2. **연기 (소비자 생기면):** S15b agy-LEAD MCP 호스팅 스파이크, S16c/d/e 매니페스트/triage 스키마 동결.
3. **main 머지:** 라이브 게이트 통과 후 s15~s18 통합.

상세 계획·결정은 [s13-next-phase-roadmap.md](s13-next-phase-roadmap.md) · [s11-multi-cli-plan.md](s11-multi-cli-plan.md) 참조.

---

## 블로커

없음

---

## 문서 맵

| 문서 | 용도 | 언어 |
|------|------|------|
| [STATUS.ko.md](STATUS.ko.md) | **사람용 현황판** (본 문서) | 한글 |
| [PROGRESS.ko.md](../PROGRESS.ko.md) | 진행 로그 + 완료 아카이브 | 한글 |
| [PROGRESS.md](../PROGRESS.md) | 에이전트용 롤링 트래커 (영문 소스, 본 문서가 미러) | 영문 |
| [IMPLEMENTATION.md](IMPLEMENTATION.md) | S0–S18 마일스톤 스펙 (스키마·MCP·플래그) | 영문 |
| [s13-next-phase-roadmap.md](s13-next-phase-roadmap.md) | S13→S18 로드맵 | 영문 |
| [s11-multi-cli-plan.md](s11-multi-cli-plan.md) | S11/S12 멀티-CLI 계획 (D1~D12, 검증 게이트) | 영문 |
| [architecture.md](architecture.md) | 아키텍처·백엔드·세션 디렉터리·데몬 수명주기 | 영문 |
| [s1-api-sketch.md](s1-api-sketch.md) ~ [s9-api-sketch.md](s9-api-sketch.md) | 단계별 구현 청사진 | 영문 |
| [../tests/manual/LIVE-GATES.md](../tests/manual/LIVE-GATES.md) · [ubuntu-attended-runbook.md](../tests/manual/ubuntu-attended-runbook.md) | 라이브 게이트 인덱스 + Linux/tmux 런부크 | 영문 |
| [superpowers/specs/](superpowers/specs/) · [superpowers/plans/](superpowers/plans/) | 설계 스펙·구현 계획 | 영문 |
| [blueprints/status.html](blueprints/status.html) | 시각 현황·게이트 | 한글 UI |
| [blueprints/s7-tui.html](blueprints/s7-tui.html) | S7 TUI 와이어프레임 | 한글 UI |
| [PRD.md](PRD.md) | 제품 요구사항 | 영문 |
| [RGIO.md](RGIO.md) | 모듈 계약 | 영문 |
