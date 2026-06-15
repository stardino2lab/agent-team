# S12a manual checklist — gemini as teammate

Prereq: G0/G1 + D12-analog in s12-gemini-gates.md PASS.

- [ ] In a fixture project's `.agent-team/config.yaml`, add `gemini-implementer`
      (and/or `gemini-planner`) to `allowed_personas`.
- [ ] Start a session (claude lead). Approve a `spawn_teammate(persona=
      "gemini-implementer", ...)`.
- [ ] Confirm: a gemini pane launches with `--approval-mode yolo --skip-trust`
      (interactive), reads its brief (AGENTS.md), runs `agent-team teammate ready`,
      and mails the lead — all WITHOUT manual approval/trust prompts.
- [ ] Confirm D10 transcript `{session_dir}/teammates/<name>/transcript.log` grows.
- [ ] Confirm the lead never named the gemini CLI/flags (decoupling invariant).
- [ ] Cost: confirm the heavy coding role ran on gemini (unlimited quota), not
      claude/codex.
