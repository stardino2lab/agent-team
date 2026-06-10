"""ProjectLoader unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_team._io import InvalidPathSegmentError
from agent_team.project_loader import (
    PlaybookLoadError,
    PlaybookNotFoundError,
    ProjectConfigError,
    ProjectLoader,
    TeamMdNotFoundError,
)


def test_load_config_and_team_md(consumer_project: Path) -> None:
    loader = ProjectLoader(consumer_project)
    config = loader.load_config()
    team_md = loader.load_team_md()

    assert config["default_playbook"] == "new-feature"
    assert "payment-api" in team_md
    assert "FastAPI" in team_md


def test_load_playbook_default(consumer_project: Path) -> None:
    loader = ProjectLoader(consumer_project)
    playbook = loader.load_playbook()
    assert playbook["name"] == "new-feature"
    assert playbook["mode"] == "guide"


def test_build_lead_context_sections(consumer_project: Path) -> None:
    loader = ProjectLoader(consumer_project)
    ctx = loader.build_lead_context(extra_context="Add refund API")

    assert "--- TEAM.md ---" in ctx.text
    assert "--- Project config ---" in ctx.text
    assert "playbook_mode: guide" in ctx.text
    assert "--- Playbook: new-feature ---" in ctx.text
    assert "--- Extra context ---" in ctx.text
    assert "Add refund API" in ctx.text
    assert ctx.playbook_name == "new-feature"
    assert ctx.playbook is not None
    assert ctx.config["allowed_personas"]


def test_missing_config_raises(tmp_path: Path) -> None:
    loader = ProjectLoader(tmp_path)
    with pytest.raises(ProjectConfigError):
        loader.load_config()


def test_missing_team_md_raises(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    agent_dir = project / ".agent-team"
    agent_dir.mkdir(parents=True)
    (agent_dir / "config.yaml").write_text("default_playbook: new-feature\n", encoding="utf-8")

    loader = ProjectLoader(project)
    with pytest.raises(TeamMdNotFoundError):
        loader.load_team_md()


def test_missing_playbook_raises(consumer_project: Path) -> None:
    loader = ProjectLoader(consumer_project)
    with pytest.raises(PlaybookNotFoundError):
        loader.load_playbook("nonexistent")


def test_playbook_path_traversal_rejected(consumer_project: Path) -> None:
    loader = ProjectLoader(consumer_project)
    with pytest.raises(InvalidPathSegmentError):
        loader.load_playbook("../config")


def test_invalid_playbook_yaml_raises(consumer_project: Path) -> None:
    playbook_path = consumer_project / ".agent-team" / "playbooks" / "new-feature.yaml"
    playbook_path.write_text("not a dict\n", encoding="utf-8")

    loader = ProjectLoader(consumer_project)
    with pytest.raises(PlaybookLoadError):
        loader.load_playbook("new-feature")


def test_invalid_config_yaml_raises(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    agent_dir = project / ".agent-team"
    agent_dir.mkdir(parents=True)
    (agent_dir / "config.yaml").write_text("just a string\n", encoding="utf-8")

    loader = ProjectLoader(project)
    with pytest.raises(ProjectConfigError):
        loader.load_config()
