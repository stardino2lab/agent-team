"""agent-team init CLI tests."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from agent_team.__main__ import main


def test_init_creates_project_files(tmp_path: Path) -> None:
    project = tmp_path / "my-api"
    project.mkdir()
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--project", str(project)])

    assert result.exit_code == 0
    assert (project / "TEAM.md").exists()
    assert (project / ".agent-team" / "config.yaml").exists()
    assert (project / ".agent-team" / "playbooks" / "new-feature.yaml").exists()
    assert (project / ".agent-team" / "personas").is_dir()


def test_init_refuses_without_force(tmp_path: Path) -> None:
    project = tmp_path / "my-api"
    project.mkdir()
    (project / "TEAM.md").write_text("# existing\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["init", "--project", str(project)])

    assert result.exit_code == 1
    assert "already exists" in result.output


def test_init_force_overwrites(tmp_path: Path) -> None:
    project = tmp_path / "my-api"
    project.mkdir()
    (project / "TEAM.md").write_text("# old\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["init", "--project", str(project), "--force"])

    assert result.exit_code == 0
    assert "my-api" in (project / "TEAM.md").read_text(encoding="utf-8")
