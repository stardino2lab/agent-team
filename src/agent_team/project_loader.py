"""Load consumer project context for team lead."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


class ProjectConfigError(ValueError):
    """Raised when project config is missing or invalid."""


class TeamMdNotFoundError(FileNotFoundError):
    """Raised when TEAM.md is missing."""


class PlaybookNotFoundError(FileNotFoundError):
    """Raised when a playbook file is missing."""


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

    def _playbook_path(self, name: str) -> Path:
        return self.project_path / ".agent-team" / "playbooks" / f"{name}.yaml"

    def load_config(self) -> dict:
        path = self._config_path()
        if not path.exists():
            raise ProjectConfigError(f"Missing config: {path}")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ProjectConfigError(f"Invalid config YAML: {path}")
        return data

    def load_team_md(self) -> str:
        path = self._team_md_path()
        if not path.exists():
            raise TeamMdNotFoundError(f"Missing TEAM.md: {path}")
        return path.read_text(encoding="utf-8")

    def load_playbook(self, name: str | None = None) -> dict:
        config = self.load_config()
        playbook_name = name or config.get("default_playbook")
        if not playbook_name:
            raise PlaybookNotFoundError("No playbook name provided and default_playbook unset")

        path = self._playbook_path(playbook_name)
        if not path.exists():
            raise PlaybookNotFoundError(f"Playbook not found: {path}")

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise PlaybookNotFoundError(f"Invalid playbook YAML: {path}")
        return data

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
