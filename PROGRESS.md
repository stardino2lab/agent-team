# Progress

## Current: S13~S18 로드맵 전체 코드 완료 @ 2026-06-21 — 410 passed/1 skipped, ruff clean. 남은 건 라이브 게이트(아래 인덱스) + 소비자-부재 연기(S15b, S16c/d/e). main 머지 미실시(s15~s18 브랜치).

## Last completed: G1+Gs 라이브 실행 + Ubuntu(claude+codex) 준비 push @ 2026-06-22

## 라이브 게이트 인덱스 (제가 못 돌림 — 사용자 실행) @ 2026-06-21

코드는 전부 단위테스트됨. 토큰/Linux/헤드리스가 필요한 검증만 체크리스트로 남김.

| 게이트 | 파일 | 검증 대상 | 상태 |
|---|---|---|---|
| G5 헤드리스 E2E (캡스톤) | `tests/manual/s18c-headless.md` | 무인 자율: start→외부승인→작업→종료→`final` 매니페스트, timeout/stop/SIGTERM/crash 변형, 헤드리스 Linux | 대기 |
| S18b 데몬 수명주기 | `tests/manual/s18b-daemon-lifecycle.md` | graceful stop/exit-code, `--timeout` kill-all, `final`/terminal status, SIGTERM graceful, crash→stop 리퍼 | 대기 |
| S18a 외부 승인자 | `tests/manual/s18a-external-approver.md` | Hermes approve/deny, TUI 안 열림, `decided_by:hermes` | 대기 |
| S17 worktree 격리 (G6) | `tests/manual/s17-worktree-gates.md` | 두 writer 같은 파일 격리/머지/prune, Windows 경로길이·락 | 대기 |
| S14 status 게이트 (Gs) | `tests/manual/s14-status-gates.md` | 실제 dead-pane, transcript mtime 전진 | free+dead-detect **PASS**(Win) · **mtime-falsepos FAIL**(Win transcript 안 자람, 아래) |
| S13c tmux Linux (G3/G4) | `tests/manual/s13-tmux-linux.md`, `tests/manual/ubuntu-attended-runbook.md` | Linux tmux 멀티페인/kickoff/dead-detect (tmux≥3.4) + claude lead+codex 티미 유인 | 대기 (런부크 준비됨, codex 서브밋키 Linux 디폴트 land) |
| S15a/S12 agy 토큰 (G1) | `tests/manual/s12-agy-gates.md` | agy 티미 라이브: kickoff, auto-approve, helper-under-agy | G0 PASS · G1 부분: agy auto-approve+helper+no-trust PASS(Win), 자동 kickoff **cold=FAIL(drop)**/warm=OK · 버그2(아래) |

**연기 (소비자 없어서):** S15b agy-LEAD (agy `mcp` 서브커맨드 부재 → MCP 호스팅 스파이크 필요), S16c/d/e (실제 Hermes 생겨야 매니페스트/triage 스키마 동결).

### Gs(S14) 라이브 실행 + Ubuntu 준비 @ 2026-06-22 (Windows + WSL 정찰)
- **Gs free 체크 PASS:** `status --json`(members/task_counts/panes_available/overall_ok), `--no-panes`(panes_available:false, running→unknown), exit 코드(healthy=0/bad-id=1/unhealthy=2).
- **Gs dead-detect PASS:** 리드 페인 kill → `health:dead`, `overall_ok:false`, escalation `member dead`, exit 2.
- **Gs mtime-falsepos FAIL [OPEN 버그, Win 전용]:** `pipe_pane`가 `cat >> file`을 PowerShell 페인서 실행 → `cat`=Get-Content라 stdin 안 흘림 → 전 Windows 티미 transcript.log **0 bytes 동결**. 무출력 장기작업 중 last_activity heartbeat 죽음 → 600s 후 STALE 오탐. **Ubuntu(bash)는 `cat>>` 정상이라 무관.** 처방 plan-eng-review 완료(1A), 구현 연기(Win 전용·메인은 Ubuntu).
- **codex Linux 서브밋키 [FIXED, `7946deb`]:** `CliSpec.teammate_submit_keys_posix` 추가, codex=Tab+Enter를 非win32 디폴트로. env `AGENT_TEAM_SUBMIT_KEYS_CODEX`로 라이브 토글. claude=Enter 유지. 411 passed.
- **Ubuntu 준비 push:** `s18` origin push(`7946deb` 코드 + `247a14b` 런부크). 내일 Ubuntu 24서 `git clone … && git checkout s18` → `tests/manual/ubuntu-attended-runbook.md` 따라 claude lead+codex 티미 유인 검증(=G3/G4). **주의: tmux≥3.4, Linux 네이티브 claude+codex 인증 필요**(WSL 22.04=tmux 3.2a + /mnt/c Windows 바이너리라 검증 부적합).
- **새 TODO:** Hermes 헤드리스 리드(trust-bypass+자동kickoff+G5), 非PowerShell 쉘 transcript — `TODOS.md`.

### G1 라이브 실행 발견 @ 2026-06-21 (Windows, 한글 로케일)
agy 티미는 `--dangerously-skip-permissions`로 **trust 모달 없이** 부팅, 툴콜 **per-command 승인 없이** 자동실행, `agent-team teammate ready/mail/task` **헬퍼 Windows 동작** — agy 능력 자체 PASS (hello.txt 생성 확인). 단 라이브 중 버그 2개:

- **[FIXED] cp949 디코드 크래시** (`psmux_backend._run`): `subprocess.run(text=True)`가 인코딩 미지정 → 한글 Windows 로케일(cp949)로 psmux 출력(박스문자 `─`=`e2 94 80`/불릿/한글) 디코드 시도 → 리더 스레드 `UnicodeDecodeError` → orchestrator 크래시. `encoding="utf-8", errors="replace"` 추가로 수정. 단위테스트 못 잡음(mock psmux). 410 passed 유지.
- **[OPEN] agy cold-boot kickoff drop** (`teammate_runner._wait_until_input_ready`): "출력 안정=입력준비" 휴리스틱이 agy의 즉시 그려지는 정적 splash 배너에 ~0.5초만에 settle → 인터랙티브 컴포저 준비 전 kickoff send_keys → **키 유실**. cold 폴더서 재현(run1, g1c), warm 폴더선 우연히 성공(g1b) = 레이스. agy는 kickoff 도착하면 정상동작(수동 재전송으로 확인). **G5 자율의 전제**. 처방: kickoff 전송 후 페인 변화 검증+재전송(CLI-중립). agy 실사용 시점에 수정.

부수 관찰(버그 아님): 리드 claude는 bare 런치라 새 폴더 첫실행 trust 모달 + 초기 user 메시지 필요 → **헤드리스(G5) 봉쇄 요인**, 사전 trust 시드 + 리드 kickoff 자동화 필요.

## S15c~S18 구현 @ 2026-06-21 (브랜치 s15~s18, plan→N-리뷰→구현→N-리뷰→커밋 루프)

per-step 전문가 리뷰가 구현 전 BLOCKING 차단. 332→410 테스트, 단계별 커밋.

- **S15c [2ca2442, s15]** cost-aware 역할→CLI: `role_cli_overrides`(persona명 키, `is_teammate_supported` 검증) + `agy-tester` persona(bundled↔root 미러). 리뷰 BLOCKING: override가 기록만 바꾸고 런치 CLI는 persona 기본값 재유도 → `orchestrator._spawn_one`→`teammate_runner.spawn(cli=)`로 승인 cli 관통.
- **S16a/b [79e01e5, s16]** Hermes 결과 매니페스트: 신규 `manifest.py` 순수 투영(`build_manifest`) + `logs manifest` CLI(json/jsonl/md) + 세션종료 `result_manifest.json` 캐시. **두 번째 진실원본 없음** — 기존 store들 read-time 투영. status 도출: completed / in_progress→abandoned(stopped시) / pending→blocked(미충족 dep, 누락 dep=blocked fail-safe). S16c/d/e 연기.
- **S17 [dcf4fb2, s17]** worktree 격리(봉쇄): `isolate_worktrees` 플래그 + `workspace-write` persona만 자기 `git worktree`에서 실행. spawn시 생성(멱등/크래시 고아 자가치유), shutdown시 prune. 생성 실패=하드스톱(공유 체크아웃 폴백 금지). 자율운영 전제.
- **S18a [e17bae6, s18]** 외부 승인자 CLI `approvals`(list/approve/deny) — Hermes가 TUI 없이 spawn 승인, spawn 게이트 불변(승인자만 프로그램으로). `SpawnRequestNotFoundError`→`CLI_ERRORS`.
- **S18b1 [f38f070, s18]** graceful `stop` + 공유 `block_until_stopped`(stop 마커 폴링, 종료코드). 이벤트→마커 순서(매니페스트 race 방지), 시작시 stale 마커 클리어.
- **S18b2 [893b1b2, s18]** `--timeout`/`--autonomous`(autonomous는 timeout 필수) + 종료시 kill-all-panes + 매니페스트 `final` 불린/terminal `session_status`. **Hermes는 `final=true`에만 반응**(중간 읽기 위험 차단). MANIFEST_VERSION 2.
- **S18b3 [351a50d, s18]** SIGTERM graceful 종료 매니페스트(컨테이너/`kill` → abrupt death 대신 클린 매니페스트, 헤드리스 Linux 의미) + `stop` 고아 pane 리퍼(크래시한 orchestrator의 auto-approve 티미 정리). 크래시 후 재생성은 코드 불요(S16a 순수 투영).
- **S18c [b738b33, s18]** 헤드리스 자율 E2E 게이트 체크리스트(G5) — 코드 없음.

## S11/S12 live e2e (Windows, real CLIs) @ 2026-06-20

## S11/S12 live e2e (Windows, real CLIs) @ 2026-06-20

Run from an isolated AGENT_TEAM_HOME + worktree sandbox, driving psmux panes directly
(send-keys / capture-pane). Recorded in `tests/manual/s11b-teammate-hardening.md` (D11b)
and `tests/manual/s11c-codex-lead.md`.

- **codex submit-keys, per platform (D11b):** raw codex on Windows (0.139.0, tmux 3.3.5)
  submits the kickoff on **Enter alone** — Tab+Enter is the LINUX value. Flipped the
  registry codex default back to `("Enter",)`; Linux drives Tab+Enter via
  `AGENT_TEAM_SUBMIT_KEYS_CODEX` (env override; platform defaulting deferred to S13).
- **Full e2e — claude lead + codex teammate (D11b Step B): PASS.** claude lead booted,
  connected to the agent-team MCP under `--strict-mcp-config`, called `spawn_teammate`;
  TUI approval works (lowercase `y`); the codex teammate auto-submitted its kickoff
  (Enter), read its brief, ran `agent-team teammate ready` → `teammate_ready` fired, and
  mailed the lead `DONE2`. The Windows Enter default is validated end-to-end in the real
  team flow. (claude submits on Enter too — Step C.)
- **codex-as-lead (S11c): FAIL.** The profile + `codex exec` launch are correct and codex
  adopts the orchestration-only role, but codex **never loads the agent-team MCP** — it
  saw only its built-in `collab` tools (spawn_agent/wait_agent), spawned a codex-internal
  agent, and exited (events.jsonl = `session_started` only). Likely: codex doesn't load
  `mcp_servers` from a `--profile` overlay (+`--ignore-user-config`). **claude remains the
  only working lead.**
- **Two blockers found, both flagged as follow-up tasks:**
  - codex **update-nag**: the 1st codex teammate after a version bump hits codex's
    interactive "Update available" prompt; the kickoff's Enter selects "Update now" and the
    pane dies (the Windows root cause of the "pane auto-terminates" symptom). Fix in
    progress (`-c check_for_update_on_startup=false`).
  - codex-lead **MCP delivery** spike (inline `-c` MCP config candidate).
- Other: D10 transcript stayed 0 bytes for the codex pane (capture gap, recheck); D12
  trust/approval OK (folder pre-trusted); orchestrator has no dead-pane health check (S14).

- Heterogeneous team (claude+codex) built `PaymentService.refund` + tests under a
  claude/Opus lead; `pytest tests/ -q` → 4 passed, reviewer APPROVED. Real
  `teammate_ready` handshake, mail/task/shutdown, full events.jsonl audit trail.
- Full suite: **216 passed**, ruff clean. Plan for next phase: `docs/s11-multi-cli-plan.md`.

## S11a implementation ($20-lead hardening: D6/D8/D9) @ 2026-06-15

- `project_loader.py` — `LEAD_ORCHESTRATION_PREAMBLE` prepended in `build_lead_context` (D6): locks the lead's low-token property structurally (orchestrate-only, no self-coding) for any gated CLI; folds in the D8 no-shell-polling line (use `wait_for_event`) and a terse-output line. No playbook can turn the lead into a coder.
- `mcp_server.py` — two new MCP tools (D8): non-blocking `get_recent_events(since, limit)` + blocking `wait_for_event(types, since, timeout)`, event-driven via `watchfiles` (immediate check → watch `session_dir` bounded by a monotonic deadline; `_DEFAULT_WAIT_TIMEOUT=60`, `_WAIT_SAFETY_SLICE_MS=500`). The lead makes ONE blocking call and burns no tokens while waiting — replaces shell-loop polling, the biggest S10 lead-token waste. **MCP tool count 9 → 11.** `_map_tool_error` widened with `OSError`.
- D9 bounded/filtered reads: `EventLog.read(limit=)` tail (`tail()` delegates); `read_inbox`/`handle_read_messages`/`read_messages` gain an exact `from_` sender filter composing with `since`; `reconcile_handled` bounds its ingest with `_RECONCILE_EVENT_TAIL=2000` (correctness rests on `session.json`, so an aged-out event at worst re-logs one error, never double-spawns).
- +11 tests (D6×1, D9-read×1, D9-from_×2, D8-get×1, D8-wait×5, D9-reconcile×1). **227 passed** (+11), ruff clean.

## S11b implementation (observability/reliability: D10/D11/D12) @ 2026-06-15

- `cli_registry.py` — `CliSpec.teammate_launch_args: tuple[str, ...] = ()` (D12); codex gets `("--dangerously-bypass-approvals-and-sandbox",)` so its teammate pane runs hands-off (no per-command approval / sandbox / first-run trust prompt). Read by the RUNNER from the registry, never named by the lead — keeps the lead/teammate CLI-decoupling invariant.
- `psmux_backend.py` — `capture_pane(target) -> str` (D11, `capture-pane -p`; mock returns "") and `pipe_pane(target, log_path)` (D10, `pipe-pane -o 'cat >> "<abs forward-slash path>"'`; `as_posix()` so Windows backslashes aren't mangled by the pane shell). Both validate the pane target.
- `teammate_runner.py` — `spawn` non-mock branch now: applies registry launch args (D12 `" ".join([cli, *launch_args])`), pipes the pane to `{session_dir}/teammates/<name>/transcript.log` (D10), then `_wait_until_input_ready` (D11, CLI-neutral capture-pane settle/timeout, `_READY_*` constants) before the kickoff so the first keystrokes don't drop during CLI startup. Transcript lives on disk only — never enters lead context (D6), zero lead tokens.
- `tests/conftest.py` — autouse `_fast_teammate_readiness` fixture patches all three `_READY_*` constants so spawn-calling unit tests don't burn the real timeout (mock `capture_pane` never settles → instant fallback).
- `cli/logs.py` — `logs export --to <dir>` writes a bundle DIRECTORY: `events.jsonl` + `transcripts/<name>.log` per teammate with a captured transcript (was a single events file).
- Live behavior (real pipe-pane on Windows, codex no-approval run, capture-pane readiness) is mocked in unit tests — verified manually via `tests/manual/s11b-teammate-hardening.md`.
- +10 tests (D12×2, capture_pane×2, pipe_pane×2, readiness-helper×2, spawn-wiring×2; logs export updated in place). **237 passed** (+10), ruff clean. Existing `test_spawn_passes_persona_cli_to_split_pane[implementer-codex]` updated to a substring check (the codex command now carries the bypass flag, so the literal CLI name is no longer a standalone argv element).

## S11c implementation (codex as 2nd verified lead: D1/D2/D3/D4) @ 2026-06-15

- `cli_registry.py` — `CliSpec.mcp_format: str | None = None` (after `teammate_launch_args`). New invariant: a lead-capable CLI requires `mcp_format`; `mcp_format="json"` also requires `mcp_config_filename`. **D3/D4:** codex flipped `supports_lead=True`, `mcp_format="toml"` (filename stays `None` — codex uses a CODEX_HOME profile, not a session-dir file); claude `mcp_format="json"`. Module docstring + antigravity note retargeted S11→S12.
- `orchestrator.py` **(D2)** — `_write_lead_mcp_config` is now format-dispatched on `CliSpec.mcp_format`: claude writes the JSON file as before; codex renders a CODEX_HOME profile `{CODEX_HOME}/agent-team-<sid>.config.toml` (via `_render_codex_profile_toml`, `json.dumps` → valid Windows-safe TOML, parsed by `tomllib` in tests). New helpers `_codex_home` (honors `$CODEX_HOME`), `_codex_profile_name`, `_lead_mcp_server_config` (shared server entry), `_write_codex_lead_agents_md` (lead context → `{session_dir}/lead/AGENTS.md`, codex's working root), and `_CODEX_LEAD_BOOTSTRAP`.
- `orchestrator.py` **(D1/D3)** — `_build_lead_launch_command` gains a `codex` arm: `codex exec --ignore-user-config --skip-git-repo-check --profile agent-team-<sid> -C "<lead dir>" -o "<last>" "<bootstrap>"`. Only a shell-safe profile name + double-quoted paths/prompt on the line (no inline `-c`). Signature widened (all kwargs optional); defensive arm message retargeted S11→S12.
- `orchestrator.py` **(D4)** — `start()` branches on `spec.mcp_format`: claude keeps the JSON + `--append-system-prompt-file` path; codex writes the working-root lead AGENTS.md and launches `codex exec` with the profile. Partial-start `except` also unlinks the CODEX_HOME profile (it lives outside `session_dir`, so `rmtree` misses it). Lead selection is config-driven (`config.yaml: lead_cli`) — flipping to/from codex is a one-line revert (cost dial).
- The live codex-as-lead E2E (does codex actually launch, load the profile under `--ignore-user-config`, connect MCP, orchestrate autonomously) is NOT auto-tested — it is the `tests/manual/s11c-codex-lead.md` checklist (the profile-load is the key live unknown). `docs/s11-multi-cli-plan.md` D3 carries the profile-deviation note.
- +8 unit tests (registry ×3 new + 3 updated; write-config ×2; launch-line ×1; codex start ×1), −2 removed codex parametrize cases (now a supported lead); `test_cli_start_attach` unsupported-lead test re-pointed codex→antigravity. **242 passed**, ruff clean. NO test wrote into the real `~/.codex` — CODEX_HOME is redirected to tmp via `monkeypatch.setenv` in every codex test.

## S12a implementation (agy as teammate — replaces gemini) @ 2026-06-19

Redirected from gemini to **agy** (Antigravity CLI, v1.0.10, Claude-Code-derived).
The gemini S12a slice (registry entry + `gemini-*` personas + 6 tests) was
**superseded** — removed, not kept alongside. Spec/plan:
`docs/superpowers/specs/2026-06-19-s12a-agy-teammate-design.md`,
`docs/superpowers/plans/2026-06-19-s12a-agy-teammate.md`.

- `cli_registry.py` — registered `agy` `CliSpec` (replaced `gemini`): `supports_teammate=True`, `supports_lead=False` (lead deferred — agy has no `mcp` subcommand, so it can't yet host the agent-team MCP server), `mcp_config_filename=None`, `mcp_format=None`. `teammate_launch_args=("--dangerously-skip-permissions",)` — agy is Claude-Code-derived, so a single interactive auto-approve flag (confirmed in `agy --help`) covers all tool approvals (replaces gemini's `--approval-mode yolo --skip-trust` pair). INTERACTIVE (the teammate runs in a pane + gets the send_keys kickoff), NOT `-p`/`--print` (headless single-shot, which would exit before the kickoff). Read by the RUNNER from the registry — lead/teammate decoupling intact. `antigravity` (the long product-name string) stays unregistered as the tests' unsupported stand-in; `agy` is the registered binary name.
- `bundled/personas/agy-implementer.yaml` + `agy-planner.yaml` (mirrored byte-for-byte into root `personas/` for the parity invariant) — `cli: agy` (heavy coding + planning). Spawned via the generic teammate path (no new launch builder); the runner applies the registry's interactive auto-approve arg. **Opt-in**: a project must add them to `allowed_personas` — no default/fixture/template config includes them, so existing claude/codex teams are unaffected.
- `orchestrator.py` — the two defensive lead-not-supported hint messages retargeted `antigravity/gemini` → `antigravity/agy` (still match `"S12"`, the only asserted substring).
- Live agy behavior (interactive launch, auto-approve, first-run trust prompt, the `agent-team` shell helper under agy) is NOT auto-tested — it needs the real binary + tokens + auth. It is `tests/manual/s12-agy-gates.md`: G0 (no-token: version/exit, `--dangerously-skip-permissions`, `-p/--print`, no `mcp` subcommand) is **DONE/PASS** on this box; G1 + helper-under-agy are the remaining token gates. Lead is blocked on an MCP spike (how agy hosts an MCP server — `.mcp.json`? `agy plugin import claude`?).
- Test count unchanged at **248 passed** (the 6 gemini cases were swapped 1:1 for agy — registry ×2, persona load ×1, spawn auto-approve ×1, parametrize case ×1, bundled importlib/parity set), ruff clean.

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

Remaining: the S10d manual E2E **run** (human-driven; see below).

### S10d — manual E2E gate (2026-06-15) — PASSED

Ran the full payment-api E2E with real CLIs. A heterogeneous team —
planner(claude) → implementer(codex) → tester(codex) → reviewer(claude),
orchestrated by a claude/Opus lead — built `PaymentService.refund` + tests,
`pytest tests/ -q` → **4 passed**, reviewer APPROVED. Real handshake fired
(`teammate_ready` only after each teammate ran `agent-team teammate ready`);
mail + task board + shutdown all worked; full audit trail in events.jsonl.

**Findings (S10+/S11 follow-ups):**
- **Teammate kickoff timing (top priority).** The kickoff `send_keys` fires
  immediately after `split_pane`, before the teammate CLI is ready for input —
  worst with codex's first-run "trust this folder?" prompt, which eats the
  keystrokes. The kickoff text *and* its Enter are dropped, so each teammate
  needed a manual nudge to start. S10a fixed the literal-"Enter" bug; this is
  the separate *input-readiness* gap. Fix options: wait for/retry until the CLI
  acks, or have the teammate auto-read its brief without a send_keys kickoff.
- **Codex work visibility.** Coordination (mail, task_claimed/completed,
  teammate_ready) is captured, but a teammate's detailed work transcript is not
  in events.jsonl (by design — it's a coordination audit, not a transcript).
  The artifact is the code/git diff. Richer per-teammate visibility would need
  pane-output capture.
- **Parallelism.** The architecture supports concurrent teammates
  (max_teammates panes + async mail/task); the lead serialized here by choice.
  Smooth parallel spawning depends on fixing the kickoff-timing gap first.

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
| S10 | done (manual E2E passed 2026-06-15) |
| S11 | a/b code-complete + live e2e @ 2026-06-20: claude-lead + codex-teammate flow PASS (Windows codex submit=Enter). **S11c codex-LEAD FAIL** — codex exec doesn't load the agent-team MCP (spike open). 2 blockers found (codex update-nag, codex-lead MCP) → follow-up tasks. See `tests/manual/s11b-teammate-hardening.md`, `s11c-codex-lead.md` |
| S12 | S12a (agy/Antigravity teammate) code-complete @ 2026-06-19, G0 live gate PASS — **G1+helper token gates NOT yet run** (pending); lead deferred (no MCP subcommand). See `tests/manual/s12-agy-gates.md` |
