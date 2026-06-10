"""agent-team init CLI tests."""

from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from agent_team.__main__ import main

BUNDLED_PLAYBOOKS = ("new-feature", "bugfix", "pr-review", "refactor")


def test_init_creates_project_files(tmp_path: Path) -> None:
    project = tmp_path / "my-api"
    project.mkdir()
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--project", str(project)])

    assert result.exit_code == 0
    assert (project / "TEAM.md").exists()
    config = yaml.safe_load((project / ".agent-team" / "config.yaml").read_text(encoding="utf-8"))
    assert config["default_playbook"] == "new-feature"
    assert ".env" in config["forbidden_paths"]
    team_md = (project / "TEAM.md").read_text(encoding="utf-8")
    assert ".env" in team_md
    for name in BUNDLED_PLAYBOOKS:
        assert (project / ".agent-team" / "playbooks" / f"{name}.yaml").exists()
    assert (project / ".agent-team" / "personas").is_dir()


def test_init_refuses_without_force(tmp_path: Path) -> None:
    project = tmp_path / "my-api"
    project.mkdir()
    team_md = project / "TEAM.md"
    team_md.write_text("# existing\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["init", "--project", str(project)])

    assert result.exit_code == 1
    assert "already initialized" in result.output
    assert team_md.read_text(encoding="utf-8") == "# existing\n"
    assert not (project / ".agent-team").exists()


def test_init_refuses_when_config_exists(tmp_path: Path) -> None:
    project = tmp_path / "my-api"
    agent_dir = project / ".agent-team"
    agent_dir.mkdir(parents=True)
    (agent_dir / "config.yaml").write_text("default_playbook: x\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["init", "--project", str(project)])

    assert result.exit_code == 1


def test_init_force_overwrites(tmp_path: Path) -> None:
    project = tmp_path / "my-api"
    project.mkdir()
    team_md = project / "TEAM.md"
    team_md.write_text("# old\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["init", "--project", str(project), "--force"])

    assert result.exit_code == 0
    content = team_md.read_text(encoding="utf-8")
    assert "# old" not in content
    assert "my-api" in content


def test_init_creates_project_directory(tmp_path: Path) -> None:
    project = tmp_path / "new-api"
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--project", str(project)])

    assert result.exit_code == 0
    assert project.is_dir()
    assert (project / "TEAM.md").exists()
