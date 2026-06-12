"""Persona catalog with layered YAML merge."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_team._io import load_yaml_dict, safe_segment
from agent_team.bundled_paths import bundled_personas_dir


class PersonaNotFoundError(LookupError):
    """Raised when a persona name is not in the registry."""


class PersonaLoadError(ValueError):
    """Raised when persona YAML is invalid."""


@dataclass
class Persona:
    name: str
    cli: str
    description: str
    spawn_prompt_template: str
    model_hint: str | None = None
    tools_hint: str | None = None
    coordination_cli: list[str] | None = None


def _persona_from_dict(data: dict) -> Persona:
    try:
        name = data["name"]
        cli = data["cli"]
        description = data["description"]
        spawn_prompt_template = data["spawn_prompt_template"]
    except KeyError as exc:
        raise PersonaLoadError(f"Missing required persona field: {exc}") from exc

    if not isinstance(name, str):
        raise PersonaLoadError("Persona name must be a string")
    safe_segment(name, "persona")
    if cli not in ("claude", "codex"):
        raise PersonaLoadError(f"Invalid cli for persona {name!r}: {cli!r}")

    coordination = data.get("coordination_cli")
    return Persona(
        name=name,
        cli=cli,
        description=description,
        spawn_prompt_template=spawn_prompt_template,
        model_hint=data.get("model_hint"),
        tools_hint=data.get("tools_hint"),
        coordination_cli=list(coordination) if coordination is not None else None,
    )


def _load_path_dir(directory: Path) -> dict[str, Persona]:
    if not directory.is_dir():
        return {}
    personas: dict[str, Persona] = {}
    for yaml_file in sorted(directory.glob("*.yaml")):
        data = load_yaml_dict(
            yaml_file.read_text(encoding="utf-8"),
            str(yaml_file),
            PersonaLoadError,
        )
        persona = _persona_from_dict(data)
        personas[persona.name] = persona
    return personas


def _load_bundled_dir() -> dict[str, Persona]:
    personas: dict[str, Persona] = {}
    root = bundled_personas_dir()
    for item in sorted(root.iterdir(), key=lambda p: p.name):
        if not item.name.endswith(".yaml"):
            continue
        data = load_yaml_dict(item.read_text(encoding="utf-8"), item.name, PersonaLoadError)
        persona = _persona_from_dict(data)
        personas[persona.name] = persona
    return personas


class PersonaRegistry:
    def __init__(
        self,
        *,
        project_path: Path | None = None,
        global_dir: Path | None = None,
    ) -> None:
        self.project_path = project_path
        self.global_dir = global_dir or Path.home() / ".agent-team" / "personas"
        self._cache: dict[str, Persona] | None = None

    def load_all(self) -> dict[str, Persona]:
        if self._cache is not None:
            return dict(self._cache)

        merged: dict[str, Persona] = {}
        merged.update(_load_path_dir(self.global_dir))
        merged.update(_load_bundled_dir())
        if self.project_path is not None:
            project_dir = self.project_path / ".agent-team" / "personas"
            merged.update(_load_path_dir(project_dir))

        self._cache = merged
        return dict(merged)

    def get(self, name: str) -> Persona:
        personas = self.load_all()
        if name not in personas:
            raise PersonaNotFoundError(f"Persona not found: {name}")
        return personas[name]

    def list_personas(self) -> list[Persona]:
        all_personas = self.load_all()
        return [all_personas[name] for name in sorted(all_personas)]

    def is_allowed(self, name: str, allowed: list[str]) -> bool:
        if name not in allowed:
            return False
        return name in self.load_all()

    def filter_allowed(self, allowed: list[str]) -> list[Persona]:
        personas = self.load_all()
        seen: set[str] = set()
        result: list[Persona] = []
        for name in allowed:
            if name in personas and name not in seen:
                result.append(personas[name])
                seen.add(name)
        return result
