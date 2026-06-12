"""Spawn teammate panes via psmux + persona prompt injection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_team._io import format_ts, utc_now
from agent_team.personas import PersonaRegistry
from agent_team.psmux_backend import PsmuxBackend

_MOCK_COMMAND = 'python -c "print(\'dry-run teammate ready\')"'


@dataclass
class SpawnResult:
    pane_id: str
    teammate_name: str
    persona: str
    cli: str
    started_at: str


@dataclass
class RecordedSpawn:
    persona: str
    teammate_name: str
    prompt: str
    pane_id: str


class TeammateRunner:
    """Compose persona prompt and start a teammate pane.

    mock=True replaces the real CLI command with a no-op print so the pane
    exits cleanly and no real LLM is launched. Whether psmux itself is real
    or mocked is the caller's choice via PsmuxBackend.
    """

    def __init__(
        self,
        psmux: PsmuxBackend,
        registry: PersonaRegistry,
        *,
        mock: bool = False,
    ) -> None:
        self.psmux = psmux
        self.registry = registry
        self._mock = mock
        self.recorded_spawns: list[RecordedSpawn] = []

    def spawn(
        self,
        *,
        psmux_session: str,
        persona: str,
        prompt: str,
        teammate_name: str,
        cwd: Path | None = None,
    ) -> SpawnResult:
        p = self.registry.get(persona)
        full_prompt = f"{p.spawn_prompt_template}\n\n{prompt}".strip()
        command = _MOCK_COMMAND if self._mock else p.cli
        pane_id = self.psmux.split_pane(psmux_session, command=command, cwd=cwd)
        if not self._mock:
            self.psmux.send_keys(pane_id, full_prompt, enter=True)
        self.recorded_spawns.append(
            RecordedSpawn(
                persona=persona,
                teammate_name=teammate_name,
                prompt=full_prompt,
                pane_id=pane_id,
            )
        )
        return SpawnResult(
            pane_id=pane_id,
            teammate_name=teammate_name,
            persona=persona,
            cli=p.cli,
            started_at=format_ts(utc_now()),
        )
