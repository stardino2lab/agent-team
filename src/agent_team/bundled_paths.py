"""Resolve bundled package assets via importlib.resources."""

from __future__ import annotations

from importlib.resources import files
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from importlib.abc import Traversable


def bundled_root() -> Traversable:
    return files("agent_team.bundled")


def bundled_personas_dir() -> Traversable:
    return bundled_root().joinpath("personas")


def bundled_playbooks_dir() -> Traversable:
    return bundled_root().joinpath("playbooks")
