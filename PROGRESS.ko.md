# 진행 상황

## 현재: S7 완료 — 다음: S8

## 최근 완료: S7 @ 2026-06-10

- Textual TUI 2×2 (Mail / Tasks / Team / Log) + spawn 승인 모달
- `agent-team tui --session ID` 및 `python -m agent_team.tui` (S8 pane용)
- 11 TUI 테스트; 전체 134 passed, 1 skipped; main 반영

## 직전: S6 @ 2026-06-10

- `mcp_server.py` — 9 MCP tools, stdio; main 반영

## 다음 액션

1. S8 plan gate → 오케스트레이터 + pane spawn 구현

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
| S8 | 예정 |
| S9 | 예정 |
| S10 | 예정 |

---

## 완료 이력 (아카이브)

### S7 — Textual TUI (2026-06-10)

- 기능: mail/task/team/log 현황 + spawn 승인 모달 (Textual pane 내부 오버레이)
- 모듈: `tui/`, `cli/tui_cmd.py`, `agent-team tui`
- 테스트: 11 TUI; 전체 134 passed, 1 skipped
- 상세: [docs/s7-api-sketch.md](docs/s7-api-sketch.md) · [docs/blueprints/s7-tui.html](docs/blueprints/s7-tui.html)

### S6 — MCP 서버 (2026-06-10)

- 기능: 팀 리드용 MCP 9 tools (spawn, mail, task, shutdown 등)
- 모듈: `mcp_server.py`
- 테스트: 21개
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
