"""Spawn teammate panes via psmux + persona prompt injection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_team._io import format_ts, utc_now
from agent_team.bundled_paths import render_bundled_template
from agent_team.personas import PersonaRegistry
from agent_team.psmux_backend import PsmuxBackend

_MOCK_COMMAND = 'python -c "print(\'dry-run teammate ready\')"'


def _kickoff_line(teammate_name: str, brief_path: Path) -> str:
    """Single-line trigger that points the teammate at its on-disk brief.

    Must stay one line: psmux send_keys types embedded newlines literally and
    each one acts as Enter in the teammate's interactive CLI, submitting the
    message line-by-line. The rich role/coordination/task context lives in the
    brief file (read from a cwd-independent absolute path), keeping the launch
    CLI-neutral — no per-CLI system-prompt flags.
    """
    line = (
        f'You are agent-team teammate "{teammate_name}". '
        f"Read your brief at {brief_path} "
        "(role, coordination CLI, and your task), then begin. "
        "Project conventions are in TEAM.md/AGENTS.md here."
    )
    return line.replace("\n", " ").replace("\r", " ")


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

    Real mode (mock=False) renders a brief to
    {session_dir}/teammates/{teammate_name}/AGENTS.md (the session scratch dir,
    never the project), runs the teammate CLI from the PROJECT root so it can
    edit files / run pytest / git, and triggers it with a single-line kickoff
    that points at the brief's absolute path.
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
            pane_id = self.psmux.split_pane(
                psmux_session, command=_MOCK_COMMAND, cwd=None
            )
        else:
            teammate_dir = session_dir / "teammates" / teammate_name
            teammate_dir.mkdir(parents=True, exist_ok=True)
            brief_path = teammate_dir / "AGENTS.md"
            brief_path.write_text(
                render_bundled_template(
                    "teammate/AGENTS.md.j2",
                    teammate_name=teammate_name,
                    persona_name=persona,
                    session_id=session_id,
                    project_path=str(project_path),
                    spawn_prompt=full_prompt,
                ),
                encoding="utf-8",
            )
            # Run the teammate CLI from the project root so relative file edits,
            # pytest, and git target the real checkout. Trigger it with a
            # single-line kickoff pointing at the absolute brief path.
            pane_id = self.psmux.split_pane(
                psmux_session, command=p.cli, cwd=project_path
            )
            # Resolve to an absolute path: the teammate runs from the project
            # cwd, so a relative brief path (possible when AGENT_TEAM_HOME is
            # relative) would not be locatable.
            self.psmux.send_keys(
                pane_id, _kickoff_line(teammate_name, brief_path.resolve()), enter=True
            )

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
