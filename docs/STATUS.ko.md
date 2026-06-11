# agent-team 구현 현황

**한 줄 요약:** S7 Textual TUI 완료 — 다음 S8 오케스트레이터 dry-run

**시각 현황:** [blueprints/status.html](blueprints/status.html) · **진행 로그:** [PROGRESS.ko.md](../PROGRESS.ko.md)

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
| S8 | 예정 | 오케스트레이터 dry-run |
| S9 | 예정 | Claude 리드 통합 (수동) |
| S10 | 예정 | payment-api E2E (수동) |

**테스트:** 134 passed, 1 skipped (`pytest tests/ -q`)

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
| S8 | 예정 | `agent-team start --dry-run` 전체 사이클 | `orchestrator.py` (미구현) |
| S9–S10 | 예정 | 실제 Claude/Codex + psmux E2E | 수동 체크리스트 |

---

## 다음 단계

1. S8 API sketch (없으면) → plan review gate (BLOCKING=0)
2. `orchestrator.py`, `teammate_runner.py`, `cli/start.py` 구현
3. code review gate → 커밋 `feat(s8): orchestrator dry-run`
4. 한글 문서 갱신

---

## 블로커

없음

---

## 문서 맵

| 문서 | 용도 | 언어 |
|------|------|------|
| [STATUS.ko.md](STATUS.ko.md) | **사람용 현황판** (본 문서) | 한글 |
| [PROGRESS.ko.md](../PROGRESS.ko.md) | 진행 로그 + 완료 아카이브 | 한글 |
| [PROGRESS.md](../PROGRESS.md) | 에이전트용 롤링 트래커 | 영문 |
| [IMPLEMENTATION.md](IMPLEMENTATION.md) | S0–S10 마일스톤 스펙 | 영문 |
| [architecture.md](architecture.md) | 아키텍처·세션 디렉터리 | 영문 |
| [s1-api-sketch.md](s1-api-sketch.md) ~ [s7-api-sketch.md](s7-api-sketch.md) | 단계별 구현 청사진 | 영문 |
| [blueprints/status.html](blueprints/status.html) | 시각 현황·게이트 | 한글 UI |
| [blueprints/s7-tui.html](blueprints/s7-tui.html) | S7 TUI 와이어프레임 | 한글 UI |
| [PRD.md](PRD.md) | 제품 요구사항 | 영문 |
| [RGIO.md](RGIO.md) | 모듈 계약 | 영문 |
