"""TeammateRunner unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_team.personas import PersonaNotFoundError, PersonaRegistry
from agent_team.psmux_backend import PsmuxBackend
from agent_team.teammate_runner import TeammateRunner, _kickoff_line


@pytest.fixture
def runner(
    psmux_backend: PsmuxBackend,
    persona_registry: PersonaRegistry,
) -> TeammateRunner:
    psmux_backend.new_session("test")
    return TeammateRunner(psmux_backend, persona_registry, mock=False)


@pytest.fixture
def mock_runner(
    psmux_backend: PsmuxBackend,
    persona_registry: PersonaRegistry,
) -> TeammateRunner:
    psmux_backend.new_session("test")
    return TeammateRunner(psmux_backend, persona_registry, mock=True)


def _spawn_kwargs(
    *,
    session_dir: Path,
    project_path: Path,
    teammate_name: str = "helper-1",
    persona: str = "planner",
    prompt: str = "Plan the auth feature.",
) -> dict:
    return {
        "psmux_session": "test",
        "persona": persona,
        "prompt": prompt,
        "teammate_name": teammate_name,
        "session_id": "demo",
        "session_dir": session_dir,
        "project_path": project_path,
    }


def test_spawn_splits_pane_and_sends_persona_prompt(
    runner: TeammateRunner,
    psmux_backend: PsmuxBackend,
    tmp_path: Path,
) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    result = runner.spawn(**_spawn_kwargs(session_dir=session_dir, project_path=project))

    assert result.pane_id.startswith("%")
    assert result.teammate_name == "helper-1"
    assert result.persona == "planner"
    assert result.cli == "claude"

    calls = psmux_backend.recorded_calls
    split = next(c for c in calls if "split-window" in c.args)
    # Teammate runs from the PROJECT root so it can edit files / run pytest / git.
    assert split.cwd == str(project.resolve())
    # Launch stays bare `persona.cli` — no per-CLI flags (CLI-neutral invariant).
    joined = " ".join(split.args)
    assert "claude" in joined
    assert "--append-system-prompt" not in joined
    assert "--mcp-config" not in joined

    send = next(c for c in calls if "send-keys" in c.args)
    keys_arg = send.args[send.args.index("-l") + 1]
    # Single-line kickoff (multi-line send_keys would submit line-by-line).
    assert "\n" not in keys_arg
    assert "\r" not in keys_arg
    assert "helper-1" in keys_arg
    # Points the teammate at its on-disk brief by ABSOLUTE path (the teammate
    # runs from the project cwd, so a relative path would not be locatable).
    brief = (session_dir / "teammates" / "helper-1" / "AGENTS.md").resolve()
    assert brief.is_absolute()
    assert str(brief) in keys_arg
    # The role/task text lives in the brief file, not in the kickoff line.
    assert "You are the Planner teammate" not in keys_arg

    assert len(runner.recorded_spawns) == 1
    assert runner.recorded_spawns[0].persona == "planner"


def test_spawn_renders_agents_md_per_teammate(
    runner: TeammateRunner,
    tmp_path: Path,
) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    runner.spawn(
        **_spawn_kwargs(
            session_dir=session_dir,
            project_path=project,
            teammate_name="helper-7",
            persona="planner",
            prompt="Plan login flow.",
        )
    )
    agents_md = session_dir / "teammates" / "helper-7" / "AGENTS.md"
    assert agents_md.exists()
    body = agents_md.read_text(encoding="utf-8")
    assert "helper-7" in body
    assert "planner" in body
    assert "demo" in body  # session_id
    assert "Plan login flow." in body
    # The multi-line persona role template lives in the brief (not the kickoff),
    # so a block-scalar template can never reach send_keys as multi-line.
    assert "You are the Planner teammate" in body


def test_spawn_mock_uses_safe_command_skips_send_keys_and_no_agents_md(
    mock_runner: TeammateRunner,
    psmux_backend: PsmuxBackend,
    tmp_path: Path,
) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    result = mock_runner.spawn(
        **_spawn_kwargs(session_dir=session_dir, project_path=project)
    )

    assert result.pane_id.startswith("%")
    calls = psmux_backend.recorded_calls
    split = next(c for c in calls if "split-window" in c.args)
    joined = " ".join(split.args)
    assert "claude" not in joined
    assert "dry-run teammate ready" in joined
    assert not any("send-keys" in c.args for c in calls)
    assert not (session_dir / "teammates").exists(), (
        "mock mode must not touch the filesystem"
    )


@pytest.mark.parametrize(
    "persona,expected_cli",
    [("planner", "claude"), ("implementer", "codex")],
)
def test_spawn_passes_persona_cli_to_split_pane(
    runner: TeammateRunner,
    psmux_backend: PsmuxBackend,
    tmp_path: Path,
    persona: str,
    expected_cli: str,
) -> None:
    """The persona's `cli` field flows verbatim into the split-pane command.

    Regression hook for cli-registry rollout: registry change must not alter
    which literal command name reaches psmux. PATH is irrelevant here —
    PsmuxBackend(mock=True) only records arguments.
    """
    project = tmp_path / "proj"
    project.mkdir()
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    result = runner.spawn(
        **_spawn_kwargs(
            session_dir=session_dir,
            project_path=project,
            teammate_name=f"helper-{persona}",
            persona=persona,
        )
    )

    assert result.cli == expected_cli
    split = next(c for c in psmux_backend.recorded_calls if "split-window" in c.args)
    # The literal CLI name reaches psmux as the head of the launch command (which
    # may also carry registry teammate_launch_args, e.g. codex's bypass flag).
    joined = " ".join(split.args)
    assert expected_cli in joined, (
        f"expected literal {expected_cli!r} in split-window args, got {split.args!r}"
    )


def test_kickoff_line_is_single_line_with_brief_path() -> None:
    brief = Path("C:/Users/x/.agent-team/sessions/s/teammates/helper-1/AGENTS.md")
    line = _kickoff_line("helper-1", brief)
    assert "\n" not in line
    assert "\r" not in line
    assert "helper-1" in line
    assert str(brief) in line


def test_kickoff_line_collapses_newlines_from_inputs() -> None:
    """Defensive: even a name carrying newlines yields a single-line kickoff."""
    line = _kickoff_line("a\nb\rc", Path("/tmp/brief.md"))
    assert "\n" not in line
    assert "\r" not in line


def test_wait_until_input_ready_settles_then_returns_true() -> None:
    from agent_team.teammate_runner import _wait_until_input_ready

    class _FakeCapture:
        def __init__(self, frames: list[str]) -> None:
            self._frames = frames
            self.calls = 0

        def capture_pane(self, target: str) -> str:
            frame = self._frames[min(self.calls, len(self._frames) - 1)]
            self.calls += 1
            return frame

    fake = _FakeCapture(["", "banner ready", "banner ready"])
    ready = _wait_until_input_ready(
        fake, "%1", poll_interval=0.0, max_wait=5.0, settle_count=2
    )
    assert ready is True
    assert fake.calls == 3  # empty, then two identical non-empty


def test_wait_until_input_ready_times_out_returns_false() -> None:
    from agent_team.teammate_runner import _wait_until_input_ready

    class _NeverReady:
        def capture_pane(self, target: str) -> str:
            return ""

    ready = _wait_until_input_ready(
        _NeverReady(), "%1", poll_interval=0.0, max_wait=0.02, settle_count=2
    )
    assert ready is False


def test_spawn_pipes_transcript_waits_then_kickoffs(
    runner: TeammateRunner,
    psmux_backend: PsmuxBackend,
    tmp_path: Path,
) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    runner.spawn(**_spawn_kwargs(session_dir=session_dir, project_path=project))

    calls = psmux_backend.recorded_calls
    # D10: the pane is piped to the teammate's transcript.log (forward-slash path).
    pipe = next(c for c in calls if "pipe-pane" in c.args)
    transcript = (session_dir / "teammates" / "helper-1" / "transcript.log").resolve()
    assert transcript.as_posix() in pipe.args[4]
    # D11: readiness was polled (capture-pane) before the kickoff was sent.
    assert any("capture-pane" in c.args for c in calls)

    def first_index(kind: str) -> int:
        return next(i for i, c in enumerate(calls) if kind in c.args)

    # Ordering: split-window → pipe-pane → capture-pane → send-keys.
    assert first_index("split-window") < first_index("pipe-pane")
    assert first_index("pipe-pane") < first_index("capture-pane")
    assert first_index("capture-pane") < first_index("send-keys")

    # Regression: a claude teammate gets NO codex bypass flag (launch_args == ()).
    split = next(c for c in calls if "split-window" in c.args)
    assert "--dangerously-bypass-approvals-and-sandbox" not in " ".join(split.args)


def test_spawn_codex_applies_bypass_launch_args(
    runner: TeammateRunner,
    psmux_backend: PsmuxBackend,
    tmp_path: Path,
) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    # 'implementer' persona has cli: codex (bundled).
    runner.spawn(
        **_spawn_kwargs(
            session_dir=session_dir,
            project_path=project,
            teammate_name="helper-impl",
            persona="implementer",
        )
    )
    split = next(c for c in psmux_backend.recorded_calls if "split-window" in c.args)
    joined = " ".join(split.args)
    # D12: codex teammate launched non-interactively, args from the registry.
    assert "codex" in joined
    assert "--dangerously-bypass-approvals-and-sandbox" in joined


def test_spawn_unknown_persona_raises(runner: TeammateRunner, tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    with pytest.raises(PersonaNotFoundError):
        runner.spawn(
            **_spawn_kwargs(
                session_dir=session_dir,
                project_path=project,
                persona="ghost",
            )
        )
