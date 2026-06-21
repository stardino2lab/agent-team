# Ubuntu attended runbook — claude lead + codex teammate

Goal: run an **attended** agent-team session on Ubuntu (you drive approvals; no
Hermes/autonomous). This doubles as the G3/G4 tmux-Linux live gate for the
claude+codex flow. agy is NOT used here.

Branch: `s18` (pushed to origin 2026-06-22).

```
flow:  install → config → start → trust lead → kickoff lead → approve codex
       → codex teammate runs (verifies Tab+Enter submit-keys) → stop
```

## 0. Prereqs (one-time)

```bash
tmux -V                      # MUST be >= 3.4 (Ubuntu 24.04 ships 3.4; 22.04 = 3.2a is too old)
which claude && claude --version   # Linux-NATIVE install, not a /mnt/c Windows binary
which codex  && codex  --version   # Linux-NATIVE; authenticate both CLIs first
python3 --version            # 3.10+
```

If tmux < 3.4: `sudo apt install tmux` on 24.04, or build 3.4+. The `-l N%` split
flag the backend uses needs >= 3.4.

```bash
git clone https://github.com/stardino2lab/agent-team.git
cd agent-team && git checkout s18
python3 -m venv .venv && . .venv/bin/activate
pip install -e .
agent-team --version         # 0.1.0
python -m pytest tests/ -q   # baseline: 411 passed, 1 skipped
```

Backend auto-selects **tmux** on Linux (no `AGENT_TEAM_BACKEND` needed).

## 1. Test project (isolated)

```bash
export AGENT_TEAM_HOME=/tmp/at-ubuntu
mkdir -p ~/at-proj/src && cd ~/at-proj
git init -q && git config user.email t@t && git config user.name t
printf 'def hello():\n    return "hi"\n' > src/app.py
printf '# at-proj\nGoal: verify claude lead + codex teammate on Ubuntu.\n' > TEAM.md
mkdir -p .agent-team
cat > .agent-team/config.yaml <<'YAML'
project_name: at-proj
max_teammates: 3
playbook_mode: guide
lead_cli: claude
allowed_personas:
  - implementer        # codex
  - reviewer           # claude
YAML
git add -A && git commit -qm init
```

## 2. Start (terminal A — blocks)

```bash
export AGENT_TEAM_HOME=/tmp/at-ubuntu
agent-team start --project ~/at-proj --session u1 \
  --context "Spawn one implementer teammate immediately for this trivial task: create src/hello.txt containing the word ok, then run 'agent-team teammate ready'. Do not code yourself."
```

## 3. Drive it (terminal B)

```bash
export AGENT_TEAM_HOME=/tmp/at-ubuntu
tmux list-panes -t u1                       # %1 (active) = lead claude, other = tui
tmux capture-pane -t %1 -p                  # if a "trust this folder?" modal: tmux send-keys -t %1 Enter
tmux send-keys -t %1 "Begin: spawn the implementer teammate now. Do not code yourself." Enter
sleep 12
agent-team approvals list --session u1 --json
agent-team approvals approve --session u1 --id apr-001 --by user
```

## 4. ★ Verify the codex teammate (the Tab+Enter check)

```bash
sleep 10
tmux list-panes -t u1                       # new pane = codex teammate
tmux capture-pane -t <new-pane> -p
```

PASS if the codex pane shows the kickoff text **submitted** and codex running
tool calls (it created `src/hello.txt`). That confirms the POSIX Tab+Enter
default works.

```bash
cat ~/at-proj/src/hello.txt                 # -> ok
agent-team status --session u1              # implementer (codex) HEALTHY
```

### If the codex composer shows the kickoff text but never SUBMITS (sits unsent)
The default Tab+Enter was wrong for your codex version. Toggle it live (no code
change), then stop + restart from step 2:
```bash
export AGENT_TEAM_SUBMIT_KEYS_CODEX="Enter"     # or e.g. "Enter Enter"
```
(Confirm which sequence submits by typing into the codex pane manually first.)

## 5. Stop

```bash
agent-team stop --session u1
tmux list-sessions                          # u1 gone
```

## Outcome
- claude lead + codex teammate full attended cycle on Ubuntu/tmux → **G3/G4 PASS**.
- Record the working `AGENT_TEAM_SUBMIT_KEYS_CODEX` value (default Tab+Enter, or
  the toggle you needed) in PROGRESS.md.
- Hermes/autonomous is OUT of scope here — see TODOS.md "Hermes headless".
