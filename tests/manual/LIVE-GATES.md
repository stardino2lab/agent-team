# 라이브 게이트 통합 런부크 (S13~S18)

**목적:** 새 스레드/사람이 이 파일 하나로 agent-team의 라이브 검증을 끝까지 돌린다.
코드는 전부 단위테스트됨(410 passed). 여기 있는 건 **토큰/실CLI/Linux/헤드리스**가
필요해 자동화 못 한 검증뿐. 각 게이트는 `tests/manual/sNN-*.md`에 상세본이 있고,
이 파일은 **순서·명령·합격기준**을 한곳에 모은 마스터.

> 새 스레드 시작 프롬프트 예: "tests/manual/LIVE-GATES.md 따라 G1부터 라이브 게이트
> 실행. 각 게이트 결과를 해당 파일 체크박스에 기록하고 PROGRESS.md 갱신."

---

## 0. 사전 상태 (읽기 전용 확인)

- 브랜치: 코드가 `s15`~`s18`에 분산(브랜치-per-S 규칙). **main 머지 안 됨.**
  최신 = `s18`. 게이트는 `s18` 체크아웃 후 실행.
  ```
  git checkout s18
  git log --oneline -12          # s15c~s18c 커밋 확인
  python -m pytest tests/ -q     # 기준선: 410 passed, 1 skipped, ruff clean
  ruff check src/ tests/
  ```
- 설치: `pip install -e .` (editable). `agent-team --version` 동작 확인.
- **격리 원칙:** 실CLI가 토큰/쿼터 쓴다. 전용 `AGENT_TEAM_HOME`(임시 디렉토리)와
  소비자 프로젝트 사본에서 돌려라. 실제 작업 체크아웃에서 돌리지 마라(티미가 파일 수정).
  ```
  export AGENT_TEAM_HOME=/tmp/at-gates      # Windows: $env:AGENT_TEAM_HOME="D:\tmp\at-gates"
  ```

---

## 게이트 순서 (의존성 순)

| # | 게이트 | 파일 | 토큰 | OS | 막힘 영향 |
|---|---|---|---|---|---|
| G1 | agy 티미 토큰 | s12-agy-gates.md | 예 | any | S15a 마감 |
| G6 | worktree 격리 | s17-worktree-gates.md | 예 | Windows OK | 자율운영 봉쇄 전제 |
| Gs | status 헬스 | s14-status-gates.md | 일부 | any | 관측성 |
| G3/G4 | tmux Linux | s13-tmux-linux.md | 예 | **Linux** | OS 독립 |
| Ga | 외부 승인자 | s18a-external-approver.md | 일부 | any | 자율 승인 |
| Gb | 데몬 수명주기 | s18b-daemon-lifecycle.md | 예 | any(SIGTERM=Linux) | 완료 계약 |
| **G5** | **헤드리스 E2E** | s18c-headless.md | 예 | **Linux** | **캡스톤** |

권장: G1 → Gs → Ga → Gb → G6 → (Linux 박스) G3/G4 → G5.

---

## G1 — agy 티미 라이브 (S15a) · 상세: `s12-agy-gates.md`

전제: agy 바이너리 설치 + 인증. G0(무토큰: version/`--dangerously-skip-permissions`/
`-p`/`mcp` 서브커맨드 부재)는 이미 **PASS**.

- [ ] `agy --dangerously-skip-permissions` 페인이 psmux `send_keys` kickoff 받고,
      per-command 승인/첫실행 trust 프롬프트 없이 툴콜 실행.
- [ ] `agent-team mail/task/teammate ready` 셸 헬퍼가 agy 밑에서 Windows 동작.
- **합격:** 위 둘 PASS → agy 티미 출하 (코드 변경 0). 결과를 s12-agy-gates.md G1에 기록.

---

## Gs — status 헬스 (S14) · 상세: `s14-status-gates.md`

- [ ] 세션 실행 중 `agent-team status --session <id> --json` → 유효 JSON
      (`members[]`, `task_counts`, `panes_available:true`, `overall_ok`).
- [ ] 티미 페인 직접 kill(`psmux kill-pane -t %N`) → 그 멤버 `DEAD`, `overall_ok:false`,
      exit 2.
- [ ] 긴 무출력 작업 중 `teammates/<name>/transcript.log` **mtime 전진**(busy인데 STALE
      오탐 안 남). 안 전진하면 → 오탐, 버퍼 낮추거나 heartbeat 추가(기록).
- **합격:** dead 감지 + mtime 전진 PASS.

---

## Ga — 외부 승인자 (S18a) · 상세: `s18a-external-approver.md`

당신이 "Hermes" 역. 한 세션에서:
- [ ] 세션 start, 리드가 `spawn_teammate` 호출 → `agent-team status`에
      `pending approval: apr-001` 표시.
- [ ] `agent-team approvals list --session <id> --json` → pending 출력
      (`request_id/persona/cli/prompt_preview`). **full prompt 노출 안 됨** 확인.
- [ ] `agent-team approvals approve --session <id> --id apr-001 --by hermes`
      → `approved apr-001 by hermes`. `resolutions.jsonl`에 `decided_by:"hermes"`,
      `events.jsonl`에 `spawn_approved`. **TUI 모달 안 열림**, 티미 spawn 됨.
- [ ] deny 경로: 다른 pending → `approvals deny ... --by hermes` → `spawn_denied`,
      페인 안 생김.
- [ ] 에러(무토큰): pending 없이 approve → exit 1 클린; 잘못된 `--id` → exit 1;
      이중 approve → 두번째 exit 1 + `resolutions.jsonl` 결의 정확히 1개.
- **합격:** 외부 approve가 hermes 귀속으로 spawn 구동, deny 차단, 에러 exit 1.

---

## Gb — 데몬 수명주기 (S18b1/2/3) · 상세: `s18b-daemon-lifecycle.md`

### S18b1 — graceful stop
- [ ] 한 터미널 `agent-team start --project <repo> --session <id>` (블록). 다른
      터미널 `agent-team stop --session <id>` → start ~1초 내 **exit 0**, `events.jsonl`에
      `orchestrator_stopped{reason:"stopped"}` **단 1개**(start 자기 emit 억제).
- [ ] graceful stop시 `result_manifest.json` 기록; `logs manifest`에 `session_stopped:true`.
- [ ] Ctrl-C → `orchestrator_stopped{reason:"user"}` 단1개, exit 0.
- [ ] **stop 후 재시작:** `agent-team attach --session <id>` 즉시종료 안 됨(stale 마커
      시작시 클리어). 다음 stop/Ctrl-C까지 유지.
- [ ] `agent-team stop --session <bad-id>` → exit 1 클린(트레이스백 없음).

### S18b2 — timeout / terminal / kill-panes / final
- [ ] `start ... --autonomous` (--timeout 없이) → exit 1 fast("--autonomous requires
      --timeout"), 페인 안 생김.
- [ ] `start ... --timeout 5` → ~5초에 `orchestrator_stopped{timeout}`, **전 페인 kill**,
      exit 0. (timeout은 attended여도 항상 teardown.)
- [ ] `start ... --autonomous --timeout <n>` → 모든 종료(timeout/stop/Ctrl-C)에 전 페인 kill.
- [ ] attended(--autonomous 없이) Ctrl-C → 페인 **안** 죽음(재attach 가능, 기존동작).
- [ ] 종료 후 `logs manifest` → `final:true` + `session_status`=terminal reason;
      실행중엔 `final:false`/`active`. **Hermes는 final로 게이팅**(중간읽기 false).

### S18b3 — SIGTERM / 리퍼 (SIGTERM은 **Linux**)
- [ ] (Linux) 백그라운드 자율 start의 pid에 `kill -TERM <pid>` → graceful,
      `orchestrator_stopped{reason:"signal"}`, 페인 kill, 매니페스트 기록(abrupt death 아님).
- [ ] `kill -9`로 orchestrator 죽임(페인 고아) → `agent-team stop --session <id>`가
      고아 페인 **리핑**(`psmux list`에서 사라짐). stop=terminate=reap.
- [ ] 크래시 후 `logs manifest` 여전히 유효 매니페스트 산출(순수 투영, 캐시 불요).
- **합격:** stop/timeout/SIGTERM/crash 4경로 모두 클린 종료 + final 계약 + 봉쇄.

---

## G6 — worktree 격리 (S17) · 상세: `s17-worktree-gates.md`

전제: 소비자 프로젝트가 **git repo(커밋 ≥1개)**, `config.yaml`에 `isolate_worktrees: true`,
`allowed_personas`에 `implementer`(+두번째 write persona).

### 무토큰
- [ ] `isolate_worktrees:true`로 start, `implementer` spawn+approve → `git -C <project>
      worktree list`에 `<session_dir>/worktrees/<name>` 표시, 티미 페인 cwd=그 worktree.
- [ ] `planner`/`reviewer`(read-only) spawn → worktree **안 생김**, 공유 루트에서 실행.
- [ ] non-git 디렉토리에 `isolate_worktrees:true` + implementer spawn → 페인 안 생김,
      `logs tail`에 `error{kind:worktree_failed}`(공유루트 폴백 없음, 좀비 페인 없음).

### 라이브 (토큰)
- [ ] **G6-two-writers:** write 티미 둘이 같은 파일을 각자 worktree에서 수정 → 공유트리 충돌 없음.
- [ ] **G6-merge:** 리드/리뷰어가 각 worktree HEAD를 머지 → 클린 머지(또는 예측가능 충돌, 무손실).
- [ ] **G6-prune:** shutdown/세션종료 → worktree 디렉토리 제거 + `worktree list`에서 사라짐.
- [ ] **G6-no-zombie:** 생성 실패시 페인 0 + git에 반쪽 worktree 등록 0.

### Windows 리스크 (기록)
- [ ] 경로길이(MAX_PATH 260): 긴 티미명으로 시도. 실패시 `git config core.longpaths true`.
- [ ] 파일락: 티미가 파일 열어둔 채 `worktree remove --force` 막히나.
- [ ] cwd가 프로젝트 외부 — pytest/AGENTS.md 탐색/git 정상 동작하나.

---

## G3/G4 — tmux Linux (S13c) · 상세: `s13-tmux-linux.md` · **Linux 박스 필요**

- [ ] tmux ≥ 3.4 설치된 Linux에서 `AGENT_TEAM_BACKEND=tmux`(또는 자동) 로 launch/멀티페인/
      kickoff/dead-detection 동작. psmux↔tmux 명령 호환(포크: `--` 구분자, `-p N`→`-l N%`).

---

## G5 — 헤드리스 자율 E2E (캡스톤) · 상세: `s18c-headless.md` · **헤드리스 Linux 필요**

무인 스크립트(=Hermes)가 사람 입력 0으로 완주:
- [ ] 헤드리스 Linux(`$DISPLAY` 없음, TTY 없음), tmux≥3.4, 티미 CLI 인증.
      **agy는 sandbox 없음 → 무인 세션 제외 또는 컨테이너/VM.** git repo +
      `isolate_worktrees:true`. **전역 유니크 세션id(uuid)**.
- [ ] `agent-team start --project <repo> --session <uuid> --autonomous --timeout <N> &`
      — 블록 안 함, 리드 페인이 detached tmux에 TTY 없이 뜸.
- [ ] `logs tail --follow`(또는 `approvals list --json`)로 각 `spawn_requested` 감지 →
      `approvals approve --id <apr> --by hermes`. TUI 안 열림.
- [ ] `logs manifest --format json` 폴링, **`final:true`에만 반응**.
- [ ] terminal 4경로(timeout/stop/SIGTERM/crash+reap) 각각 실행 → 봉쇄 유지, 매니페스트
      `session_status` = terminal reason.
- **G5 PASS:** 무인 full 사이클 완주 → agent-team이 Hermes 밑 무인 워커로 인증.
  (S16e 동결 계약 doc의 전제.)

---

## 결과 기록 위치
1. 각 게이트의 `tests/manual/sNN-*.md` 체크박스 + 발견사항.
2. `PROGRESS.md`의 "라이브 게이트 인덱스" 표 상태(대기→PASS/FAIL).
3. FAIL이면 재현 명령 + 정확한 에러 인용을 PROGRESS.md에.

## 막힌/연기 항목 (게이트 아님)
- **S15b agy-LEAD:** agy `mcp` 서브커맨드 부재 → MCP 호스팅 스파이크 필요
  (`.mcp.json`? `agy plugin import claude`? `~/.antigravity/`). 라이브 agy 조사 선행.
- **S16c/d/e:** 실제 Hermes 소비자 생겨야 매니페스트/triage 스키마 동결.
