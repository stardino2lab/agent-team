# agent-team 구현 현황

**한 줄 요약:** S10 payment-api 실토큰 E2E 통과 — 다음 S11 멀티-CLI (codex 2nd lead) + $20-lead 토큰 하드닝

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
| S8 | 완료 | 오케스트레이터 dry-run (`start`/`attach`, mock 팀원) |
| S9 | 완료 | Claude 리드 통합 — 수동 스모크 통과 (2026-06-14) |
| S10 | 완료 | payment-api 실토큰 E2E 통과 (2026-06-15) |
| S11 | 예정 | 멀티-CLI: codex 2nd lead + $20-lead 토큰/관측 하드닝 |
| S12 | 예정 | Gemini/Antigravity (G0–G6 검증 게이트 통과 후) |

**테스트:** 216 passed (`pytest tests/ -q`)

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
| S11 | 예정 | codex 2nd lead + 토큰/관측 하드닝 (D6 preamble, D8 event-driven, D9 bounded reads, D10 transcript, D11/D12 codex 팀원 비대화형) | [s11-multi-cli-plan.md](s11-multi-cli-plan.md) |
| S12 | 예정 | Gemini/Antigravity 팀원→리드 (검증 게이트 G0–G6) | 동상 |

---

## 다음 단계

1. **S11a — $20-lead 하드닝 (최우선, ROI 최고):** D6 orchestration-only preamble + D8 event-driven wait(폴링 제거) + D9 bounded/filtered reads. S10 토큰 리뷰의 직접 결과물.
2. **S11b — 관측/신뢰성:** D10 팀원 transcript 캡처 + D11 kickoff input-readiness + D12 codex 팀원 비대화형(승인/샌드박스) launch.
3. **S11c — codex 2nd lead:** D1/D2(per-CLI lead dispatch + JSON/TOML MCP 렌더러) + D3 + D4(config 기반 역할 배정, `lead_cli` 플립).
4. **S12 (병렬 spike 가능):** Gemini/Antigravity 설치 + G0–G6 검증 → S12a 팀원 → S12b 리드.

상세 계획·결정(D1~D12)·검증 게이트는 [s11-multi-cli-plan.md](s11-multi-cli-plan.md) 참조.

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
| [s11-multi-cli-plan.md](s11-multi-cli-plan.md) | S11/S12 멀티-CLI 계획 (D1~D12, 검증 게이트) | 영문 |
| [architecture.md](architecture.md) | 아키텍처·세션 디렉터리 | 영문 |
| [s1-api-sketch.md](s1-api-sketch.md) ~ [s9-api-sketch.md](s9-api-sketch.md) | 단계별 구현 청사진 | 영문 |
| [superpowers/specs/](superpowers/specs/) · [superpowers/plans/](superpowers/plans/) | S10a/S10b 설계 스펙·구현 계획 | 영문 |
| [blueprints/status.html](blueprints/status.html) | 시각 현황·게이트 | 한글 UI |
| [blueprints/s7-tui.html](blueprints/s7-tui.html) | S7 TUI 와이어프레임 | 한글 UI |
| [PRD.md](PRD.md) | 제품 요구사항 | 영문 |
| [RGIO.md](RGIO.md) | 모듈 계약 | 영문 |
