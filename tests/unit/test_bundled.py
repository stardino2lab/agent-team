"""Bundled asset parity tests."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_bundled_personas_match_root() -> None:
    root_dir = REPO_ROOT / "personas"
    bundled_dir = REPO_ROOT / "src" / "agent_team" / "bundled" / "personas"
    root_files = sorted(root_dir.glob("*.yaml"))
    bundled_files = sorted(bundled_dir.glob("*.yaml"))
    assert [f.name for f in root_files] == [f.name for f in bundled_files]
    for root_file in root_files:
        bundled_file = bundled_dir / root_file.name
        assert root_file.read_bytes() == bundled_file.read_bytes()


def test_bundled_playbooks_match_docs() -> None:
    root_dir = REPO_ROOT / "docs" / "playbooks"
    bundled_dir = REPO_ROOT / "src" / "agent_team" / "bundled" / "playbooks"
    root_files = sorted(root_dir.glob("*.yaml"))
    bundled_files = sorted(bundled_dir.glob("*.yaml"))
    assert [f.name for f in root_files] == [f.name for f in bundled_files]
    for root_file in root_files:
        assert root_file.read_bytes() == (bundled_dir / root_file.name).read_bytes()


def test_bundled_templates_match_root() -> None:
    root_dir = REPO_ROOT / "templates" / "project"
    bundled_dir = REPO_ROOT / "src" / "agent_team" / "bundled" / "templates" / "project"
    for name in ("TEAM.md.j2", "config.yaml.j2"):
        assert (root_dir / name).read_bytes() == (bundled_dir / name).read_bytes()


def test_bundled_personas_accessible_via_importlib() -> None:
    personas = files("agent_team.bundled").joinpath("personas")
    names = sorted(item.name for item in personas.iterdir() if item.name.endswith(".yaml"))
    assert names == ["implementer.yaml", "planner.yaml", "reviewer.yaml", "tester.yaml"]
