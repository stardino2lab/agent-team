# Plan: review-expert 전문가 수를 고정 5 → 필요한 N명으로 변경

## 목표

`review-expert` 스킬에서 "마일스톤 모양 → 4/5/6 고정, 기본 5" 규칙을 제거하고,
**N = 그 변경이 실제로 건드리는 리뷰 축(axis)마다 1명, 최소 1명·상한 없음, 매번 판단**으로 바꾼다.
plan(계획)·code(구현) 두 모드 모두 적용.

## 변경할 파일

1. `.cursor/skills/review-expert/SKILL.md`
2. `.cursor/skills/review-expert/axes-template.md`

(둘 다 문서. 코드/테스트 변경 없음.)

## 단계별 작업

### 1. SKILL.md — `## Expert count` 섹션 교체
- 기존: 마일스톤 모양별 4/5/6 표 + "Default 5 when unsure".
- 변경: 
  - N = 이 변경이 실제로 건드리는 리뷰 축마다 1명.
  - 최소 1명, 상한 없음. 고정 기본값 없음 — 매번 변경 범위를 보고 판단.
  - 축 후보 예시(스키마/API/테스트/보안/다운스트림/CLI-UX/패키징 등) 중 **적용되는 것만** 선택.
  - 각 expert = 하나의 focused Task.

### 2. SKILL.md — plan/code 모드 문구 정합화
- `## Mode: plan review` step 2 "Assign 4–6 expert axes" → "적용되는 축만 배정(≥1, 필요한 만큼)".
- `## Mode: code review` step 2: 동일 원칙 유지 문구 확인(이미 "Same or refined axes" — 큰 변경 없음).

### 3. axes-template.md — 체크리스트/문구 정합화
- `## Subagent launch checklist`의 "N experts defined (4–6)" → "N experts defined (≥1, one per applicable axis)".
- 상단 안내문 및 plan/code 축 표는 **예시 후보**임을 명확히 (E1~E5는 고정이 아니라 적용 시 선택).
- `## Examples from this repo`(S1=4, S2=5, S3=5)는 **과거 사례 기록**으로 유지.

## 검증 방법
- 문서 전용 변경 → 코드/테스트 영향 없음. `pytest`/`ruff` 불필요.
- 육안 검토: "5", "기본 5", "4–6" 등 고정 수치가 규칙(rule)으로 남아있지 않은지 grep 확인.
  - `rg -n "Default 5|4–6|4-6|기본 5" .cursor/skills/review-expert/`

## 위험 / 영향 범위
- 영향: review-expert 게이트 운영 방식만 바뀜. 다른 코드·테스트 무관.
- 과거 사례 수치(S1/S2/S3)는 history로 남겨 혼동 방지.
- 단일 소스(.cursor)만 수정 — AGENTS.md 참조 경로 그대로 유효.

## 예외 표기
- `## Expert count`을 규칙에서 가이드로 바꾸되, "상한 없음"이라도 실무상 과도한 분할은 피하라는 한 줄만 첨언(선택). 사용자가 원치 않으면 생략.
