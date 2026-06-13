"""agent-team init - scaffold consumer project."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from jinja2 import Environment, PackageLoader, select_autoescape

from agent_team.bundled_paths import bundled_playbooks_dir

INIT_TEMPLATES: dict[str, dict] = {
    "fastapi": {
        "stack": "FastAPI + SQLAlchemy + pytest",
        "test_command": "pytest tests/ -q",
        "lint_command": "ruff check .",
        "branch": "main",
        "notes": "FastAPI service template",
        "forbidden_paths": [".env", "secrets/", "prod-config/"],
    },
}


def _jinja_env() -> Environment:
    return Environment(
        loader=PackageLoader("agent_team.bundled", "templates/project"),
        autoescape=select_autoescape(default=False),
    )


def _copy_playbooks(target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for item in bundled_playbooks_dir().iterdir():
        if item.name.endswith(".yaml"):
            dest = target_dir / item.name
            dest.write_text(item.read_text(encoding="utf-8"), encoding="utf-8")


@click.command("init")
@click.option("--template", default="fastapi", type=click.Choice(sorted(INIT_TEMPLATES)))
@click.option("--project", type=click.Path(path_type=Path), default=".")
@click.option("--force", is_flag=True, help="Overwrite existing TEAM.md and config.")
def init_cmd(template: str, project: Path, force: bool) -> None:
    """Scaffold TEAM.md and .agent-team/ in a consumer project."""
    project = project.resolve()
    team_md = project / "TEAM.md"
    config_path = project / ".agent-team" / "config.yaml"
    agent_team_dir = project / ".agent-team"

    if not force and (team_md.exists() or config_path.exists()):
        click.echo(
            "Project already initialized (TEAM.md or .agent-team/config.yaml exists). "
            "Use --force to overwrite.",
            err=True,
        )
        sys.exit(1)

    project.mkdir(parents=True, exist_ok=True)

    preset = INIT_TEMPLATES[template]
    context = {
        "project_name": project.name,
        "stack": preset["stack"],
        "test_command": preset["test_command"],
        "lint_command": preset["lint_command"],
        "branch": preset["branch"],
        "notes": preset["notes"],
        "forbidden_paths": preset["forbidden_paths"],
    }

    env = _jinja_env()
    team_content = env.get_template("TEAM.md.j2").render(**context)
    config_content = env.get_template("config.yaml.j2").render(**context)

    team_md.write_text(team_content, encoding="utf-8")
    agent_team_dir.mkdir(parents=True, exist_ok=True)
    (agent_team_dir / "config.yaml").write_text(config_content, encoding="utf-8")
    _copy_playbooks(agent_team_dir / "playbooks")
    (agent_team_dir / "personas").mkdir(parents=True, exist_ok=True)

    click.echo(f"Created {team_md}")
    click.echo(f"Created {agent_team_dir / 'config.yaml'}")
    click.echo(f"Created {agent_team_dir / 'playbooks'}")
    click.echo(f"Created {agent_team_dir / 'personas'}")
