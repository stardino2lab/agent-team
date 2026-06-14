"""Load consumer project context for team lead."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from agent_team._io import load_yaml_dict, safe_segment

# Prepended to every lead system prompt (claude, codex, or any future gated CLI)
# so the lead's low-token property is STRUCTURAL, not a playbook convention. A
# custom TEAM.md/playbook saying "review the code yourself" cannot turn the lead
# into a high-token consumer. The text below is the spec's D6 block (see
# docs/s11-multi-cli-plan.md) plus the D8 no-shell-polling line and a terse-output
# line, since D6/D8 land together in S11a.
LEAD_ORCHESTRATION_PREAMBLE = """\
You are the team LEAD. Your only job is orchestration — not coding.

- Coordinate the team EXCLUSIVELY through the agent-team MCP tools:
  spawn_teammate, send_message, create_task, claim_task, complete_task, list_teammates.
- NEVER read, edit, write, or review project code yourself. Delegate every file read,
  edit, test run, and code review to a teammate — that is what teammates are for.
- Your only outputs are: spawn/approval decisions, task assignments, mail to teammates,
  and a final synthesis built from teammates' MAILED findings (never from raw files/diffs).
- Keep your context lean. Do not pull large files, diffs, or logs into your own context.
  If code must be understood, spawn a teammate to read it and mail you a short summary.
- Do NOT poll with shell loops or background watchers to wait for a stage to finish.
  Call wait_for_event(types, since, timeout) to block until teammates signal progress
  (teammate_ready / task_completed / mail_sent), or get_recent_events(since, limit) to
  catch up. The orchestrator emits these events for you — never arm a shell `test -f` loop.
- When reading mail or events, filter — pass since/from_/limit instead of pulling the
  whole inbox or event log into your context.
- Treat the playbook as a guide, and honor the config allowlists (max_teammates,
  allowed_personas). Spawn only with user approval; shut teammates down when their stage ends.
- Keep your own messages terse. No multi-paragraph recaps — a few lines suffice."""


class ProjectConfigError(ValueError):
    """Raised when project config is missing or invalid."""


class TeamMdNotFoundError(FileNotFoundError):
    """Raised when TEAM.md is missing."""


class PlaybookNotFoundError(FileNotFoundError):
    """Raised when a playbook file is missing."""


class PlaybookLoadError(ValueError):
    """Raised when playbook YAML is invalid."""


@dataclass
class LeadContext:
    text: str
    config: dict
    playbook_name: str | None
    playbook: dict | None


class ProjectLoader:
    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path.resolve()

    def _config_path(self) -> Path:
        return self.project_path / ".agent-team" / "config.yaml"

    def _team_md_path(self) -> Path:
        return self.project_path / "TEAM.md"

    def _playbooks_dir(self) -> Path:
        return self.project_path / ".agent-team" / "playbooks"

    def _playbook_path(self, name: str) -> Path:
        safe_segment(name, "playbook")
        return self._playbooks_dir() / f"{name}.yaml"

    def load_config(self) -> dict:
        path = self._config_path()
        if not path.exists():
            raise ProjectConfigError(f"Missing config: {path}")
        return load_yaml_dict(path.read_text(encoding="utf-8"), str(path), ProjectConfigError)

    def load_team_md(self) -> str:
        path = self._team_md_path()
        if not path.exists():
            raise TeamMdNotFoundError(f"Missing TEAM.md: {path}")
        return path.read_text(encoding="utf-8")

    def load_playbook(self, name: str | None = None) -> dict:
        config = self.load_config()
        playbook_name = name or config.get("default_playbook")
        if not playbook_name or not isinstance(playbook_name, str):
            raise PlaybookNotFoundError("No playbook name provided and default_playbook unset")

        path = self._playbook_path(playbook_name)
        if not path.exists():
            raise PlaybookNotFoundError(f"Playbook not found: {path}")

        return load_yaml_dict(path.read_text(encoding="utf-8"), str(path), PlaybookLoadError)

    def build_lead_context(
        self,
        *,
        playbook_name: str | None = None,
        extra_context: str | None = None,
    ) -> LeadContext:
        team_md = self.load_team_md()
        config = self.load_config()
        resolved_playbook_name = playbook_name or config.get("default_playbook")
        playbook = None
        if resolved_playbook_name:
            playbook = self.load_playbook(resolved_playbook_name)

        sections = [
            LEAD_ORCHESTRATION_PREAMBLE,
            "--- TEAM.md ---",
            team_md,
            "--- Project config ---",
            f"max_teammates: {config.get('max_teammates', 5)}",
            f"playbook_mode: {config.get('playbook_mode', 'guide')}",
            f"allowed_personas: {config.get('allowed_personas', [])}",
        ]
        if playbook is not None and resolved_playbook_name:
            sections.extend(
                [
                    f"--- Playbook: {resolved_playbook_name} ---",
                    yaml.safe_dump(playbook, sort_keys=False).rstrip(),
                ]
            )
        if extra_context:
            sections.extend(["--- Extra context ---", extra_context])

        text = "\n\n".join(sections)
        return LeadContext(
            text=text,
            config=config,
            playbook_name=resolved_playbook_name,
            playbook=playbook,
        )
