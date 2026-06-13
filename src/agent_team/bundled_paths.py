"""Resolve bundled package assets via importlib.resources."""

from __future__ import annotations

from importlib.resources import files
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, PackageLoader, select_autoescape

if TYPE_CHECKING:
    from importlib.abc import Traversable


def bundled_root() -> Traversable:
    return files("agent_team.bundled")


def bundled_personas_dir() -> Traversable:
    return bundled_root().joinpath("personas")


def bundled_playbooks_dir() -> Traversable:
    return bundled_root().joinpath("playbooks")


_template_env: Environment | None = None


def _env() -> Environment:
    global _template_env
    if _template_env is None:
        _template_env = Environment(
            loader=PackageLoader("agent_team.bundled", "templates"),
            autoescape=select_autoescape(default=False),
            keep_trailing_newline=True,
        )
    return _template_env


def render_bundled_template(rel_path: str, **variables: Any) -> str:
    """Render a Jinja template from src/agent_team/bundled/templates/.

    For text artifacts (AGENTS.md, TEAM.md). For JSON (MCP config), prefer
    json.dumps over Jinja so backslashes in Windows paths do not need to be
    escaped manually.
    """
    return _env().get_template(rel_path).render(**variables)
