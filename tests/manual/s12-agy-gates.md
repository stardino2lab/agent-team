# S12 agy (Antigravity) verification gates — run on THIS Windows box

Reproduce live, not inferred from docs. G0 + G1 + helper gate S12a (teammate).
Lead gates are deferred until the MCP spike (agy has no `mcp` subcommand).
agy 1.0.10.

## Free checks (no tokens) — G0 [DONE 2026-06-19]
- [x] `agy --version` → prints 1.0.10, exit 0. Launches from a non-TTY psmux pane.
- [x] `agy --help` shows `--dangerously-skip-permissions` (auto-approve all tools).
- [x] `agy --help` shows `-p/--print` + `--prompt-interactive` (headless vs interactive).
- [x] `agy help mcp` → "unknown subcommand: mcp" (confirms no MCP subcommand → lead deferred).

## Token / auth checks
- [x] G1 (teammate) — PARTIAL @ 2026-06-21 (Windows). agy pane runs tool calls WITHOUT
      per-command approval AND WITHOUT a first-run trust prompt (PASS: the assumption
      below holds — `--dangerously-skip-permissions` DOES clear the trust modal; agy
      went straight to its `>` prompt on a cold, never-trusted folder). BUT the
      auto-kickoff itself is unreliable on a COLD boot (see WATCH below): the kickoff
      send_keys DROPPED on a fresh folder (run1 + g1c), so agy sat idle at an empty
      prompt; a manual resend then ran the task fine. On a WARM folder (g1b) the
      auto-kickoff landed. So: agy capability PASS, auto-kickoff delivery = OPEN BUG.
      WATCH (CONFIRMED, root cause reclassified): the silent-hang risk is REAL but the
      failure mode is a DROPPED kickoff, not a trust-modal block. `_wait_until_input_
      ready` settles on agy's instantly-painted static splash banner (~0.5s, stable
      non-empty) BEFORE agy's interactive composer accepts input → keystrokes lost.
      It's a boot-speed RACE (cold=fail, warm=pass). Remedy is NOT trust-related:
      verify the pane changed after send_keys and resend if not (CLI-neutral), or probe
      the real input-ready marker instead of "any stable output". Deferred — agy not in
      immediate use. See PROGRESS.md "G1 라이브 실행 발견".
- [x] Helper-under-agy (teammate) — PASS @ 2026-06-21 (Windows). agy ran
      `agent-team teammate ready --session <id> --as <name>`, `agent-team mail send`,
      and `agent-team task list` from its pane; orchestrator saw it HEALTHY + created
      src/hello.txt="ok". [token]

> Also surfaced live (NOT an agy issue): a cp949 UnicodeDecodeError crashed the
> orchestrator when `psmux_backend._run` decoded pane captures (box-drawing / CJK)
> with the Windows locale codec. FIXED: forced `encoding="utf-8", errors="replace"`.
> And the LEAD claude is bare-launched → hits the first-run trust modal on a fresh
> folder and needs an initial user turn (blocks headless G5 until pre-seeded).

## Deferred (lead — needs an MCP spike)
- [ ] Resolve how agy hosts an MCP server (Claude-Code `.mcp.json` project convention?
      `agy plugin import claude`? a config file under `~/.antigravity/`?). Only then can
      agy be evaluated as a lead. Out of scope for S12a.

## Outcome
- G0 + helper PASS, G1 PARTIAL @ 2026-06-21: agy teammate CAPABILITY is trustworthy
  (no trust modal, auto-approve, helpers work), but the runner's AUTO-kickoff drops on
  a cold agy boot — must fix the kickoff verify/retry before agy is used hands-off
  (esp. headless G5). Manual kickoff works today.
- Lead is blocked on the MCP spike above.
