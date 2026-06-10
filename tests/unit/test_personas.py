"""PersonaRegistry unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from agent_team._io import InvalidPathSegmentError
from agent_team.personas import PersonaLoadError, PersonaNotFoundError, PersonaRegistry


def test_bundled_personas_load() -> None:
    registry = PersonaRegistry()
    personas = registry.load_all()
    assert set(personas) == {"planner", "implementer", "reviewer", "tester"}
    assert personas["planner"].cli == "claude"
    assert personas["implementer"].cli == "codex"


def test_project_overrides_bundled(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    personas_dir = project / ".agent-team" / "personas"
    personas_dir.mkdir(parents=True)
    override = {
        "name": "planner",
        "description": "Custom planner",
        "cli": "claude",
        "spawn_prompt_template": "Custom prompt",
    }
    (personas_dir / "planner.yaml").write_text(yaml.dump(override), encoding="utf-8")

    registry = PersonaRegistry(project_path=project)
    assert registry.get("planner").description == "Custom planner"


def test_global_persona_merged_with_bundled(tmp_path: Path) -> None:
    global_dir = tmp_path / "global-personas"
    global_dir.mkdir()
    data = {
        "name": "global-only",
        "description": "Global custom persona",
        "cli": "claude",
        "spawn_prompt_template": "Global",
    }
    (global_dir / "global-only.yaml").write_text(yaml.dump(data), encoding="utf-8")

    registry = PersonaRegistry(global_dir=global_dir)
    assert registry.get("global-only").description == "Global custom persona"
    assert registry.get("tester").description == "Test execution and verification"


def test_filter_allowed_and_is_allowed() -> None:
    registry = PersonaRegistry()
    allowed = ["planner", "unknown", "implementer"]
    filtered = registry.filter_allowed(allowed)
    assert [p.name for p in filtered] == ["planner", "implementer"]
    assert registry.is_allowed("planner", allowed) is True
    assert registry.is_allowed("unknown", allowed) is False


def test_unknown_persona_raises() -> None:
    registry = PersonaRegistry()
    with pytest.raises(PersonaNotFoundError):
        registry.get("missing")


def test_invalid_yaml_raises(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    personas_dir = project / ".agent-team" / "personas"
    personas_dir.mkdir(parents=True)
    (personas_dir / "bad.yaml").write_text("not: [valid", encoding="utf-8")

    registry = PersonaRegistry(project_path=project)
    with pytest.raises(yaml.YAMLError):
        registry.load_all()


def test_unsafe_persona_name_rejected(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    personas_dir = project / ".agent-team" / "personas"
    personas_dir.mkdir(parents=True)
    data = {
        "name": "../evil",
        "description": "bad",
        "cli": "claude",
        "spawn_prompt_template": "x",
    }
    (personas_dir / "evil.yaml").write_text(yaml.dump(data), encoding="utf-8")

    registry = PersonaRegistry(project_path=project)
    with pytest.raises(InvalidPathSegmentError):
        registry.load_all()


def test_invalid_cli_raises(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    personas_dir = project / ".agent-team" / "personas"
    personas_dir.mkdir(parents=True)
    data = {
        "name": "custom",
        "description": "bad cli",
        "cli": "gpt",
        "spawn_prompt_template": "x",
    }
    (personas_dir / "custom.yaml").write_text(yaml.dump(data), encoding="utf-8")

    registry = PersonaRegistry(project_path=project)
    with pytest.raises(PersonaLoadError):
        registry.load_all()
