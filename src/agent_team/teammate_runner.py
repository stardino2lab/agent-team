"""Spawn teammate panes via psmux + persona prompt injection."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from agent_team._io import format_ts, utc_now
from agent_team.bundled_paths import render_bundled_template
from agent_team.cli_registry import get_cli_spec
from agent_team.personas import PersonaRegistry
from agent_team.psmux_backend import PsmuxBackend

_MOCK_COMMAND = 'python -c "print(\'dry-run teammate ready\')"'

# D11 input-readiness tuning. The teammate CLI is not reading stdin the instant
# its pane is split, so an eager kickoff drops. Poll the pane until its output
# settles (CLI at its input prompt), then send. Tests patch these to be instant.
_READY_POLL_INTERVAL_S = 0.25
_READY_MAX_WAIT_S = 8.0
_READY_SETTLE_COUNT = 2


def _wait_until_input_ready(
    psmux: object,
    pane_id: str,
    *,
    poll_interval: float,
    max_wait: float,
    settle_count: int,
) -> bool:
    """Block until the teammate CLI pane looks ready for input, or max_wait (D11).

    CLI-neutral heuristic: capture the pane repeatedly; once its output is
    non-empty and unchanged across `settle_count` consecutive polls, the CLI has
    finished its startup banner and is at its input prompt. Returns True if it
    settled, False on timeout — the caller sends the kickoff either way (the
    fallback covers CLIs whose output never fully settles).
    """
    prev: str | None = None
    same = 0
    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline:
        cur = psmux.capture_pane(pane_id)
        if cur and cur == prev:
            same += 1
            if same >= settle_count:
                return True
        else:
            same = 1 if cur else 0
        prev = cur
        time.sleep(poll_interval)
    return False


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
            # D12: per-CLI launch args from the registry (e.g. codex non-interactive
            # approval/sandbox bypass). Read by the RUNNER, never named by the lead.
            spec = get_cli_spec(p.cli)
            command = " ".join([p.cli, *spec.teammate_launch_args])
            # Run the teammate CLI from the project root so relative file edits,
            # pytest, and git target the real checkout.
            pane_id = self.psmux.split_pane(
                psmux_session, command=command, cwd=project_path
            )
            # D10: capture the pane's full output to a durable per-teammate
            # transcript (coordination events + mail do NOT capture its work).
            transcript_path = teammate_dir / "transcript.log"
            self.psmux.pipe_pane(pane_id, transcript_path)
            # D11: wait until the CLI is reading stdin before the kickoff, else
            # the first keystrokes drop during CLI startup.
            _wait_until_input_ready(
                self.psmux,
                pane_id,
                poll_interval=_READY_POLL_INTERVAL_S,
                max_wait=_READY_MAX_WAIT_S,
                settle_count=_READY_SETTLE_COUNT,
            )
            # Trigger with a single-line kickoff pointing at the absolute brief
            # path. Submit keys are per-CLI (codex needs Tab+Enter; Enter alone
            # leaves the composer unsubmitted and the teammate never starts).
            self.psmux.send_keys(
                pane_id,
                _kickoff_line(teammate_name, brief_path.resolve()),
                submit_keys=spec.teammate_submit_keys,
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
