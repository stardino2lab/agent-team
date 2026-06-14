"""TeammateRunner unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_team.personas import PersonaNotFoundError, PersonaRegistry
from agent_team.psmux_backend import PsmuxBackend
from agent_team.teammate_runner import TeammateRunner


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
    # Points the teammate at its on-disk brief by absolute path.
    brief = session_dir / "teammates" / "helper-1" / "AGENTS.md"
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
    assert expected_cli in split.args, (
        f"expected literal {expected_cli!r} in split-window args, got {split.args!r}"
    )


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
