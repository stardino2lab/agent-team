"""Spawn teammate panes via psmux + persona prompt injection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_team._io import format_ts, utc_now
from agent_team.bundled_paths import render_bundled_template
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

    Real mode (mock=False) also renders AGENTS.md per teammate into
    {session_dir}/teammates/{teammate_name}/AGENTS.md and runs the teammate
    CLI from that directory so it auto-picks the file up.
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
        session_id: str,
        session_dir: Path,
        project_path: Path,
    ) -> SpawnResult:
        p = self.registry.get(persona)
        full_prompt = f"{p.spawn_prompt_template}\n\n{prompt}".strip()

        if self._mock:
            command = _MOCK_COMMAND
            pane_cwd: Path | None = None
        else:
            teammate_dir = session_dir / "teammates" / teammate_name
            teammate_dir.mkdir(parents=True, exist_ok=True)
            agents_md = render_bundled_template(
                "teammate/AGENTS.md.j2",
                teammate_name=teammate_name,
                persona_name=persona,
                session_id=session_id,
                project_path=str(project_path),
                spawn_prompt=full_prompt,
            )
            (teammate_dir / "AGENTS.md").write_text(agents_md, encoding="utf-8")
            command = p.cli
            pane_cwd = teammate_dir

        pane_id = self.psmux.split_pane(psmux_session, command=command, cwd=pane_cwd)
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
