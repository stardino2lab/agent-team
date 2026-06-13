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
    assert "claude" in " ".join(split.args)
    # split is run from the teammate dir (so AGENTS.md is picked up via cwd)
    assert split.cwd == str((session_dir / "teammates" / "helper-1").resolve())

    send = next(c for c in calls if "send-keys" in c.args)
    keys_arg = send.args[send.args.index("-l") + 1]
    assert "You are the Planner teammate" in keys_arg
    assert "Plan the auth feature." in keys_arg

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
