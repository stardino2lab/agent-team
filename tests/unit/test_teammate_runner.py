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


def test_spawn_splits_pane_and_sends_persona_prompt(
    runner: TeammateRunner,
    psmux_backend: PsmuxBackend,
) -> None:
    result = runner.spawn(
        psmux_session="test",
        persona="planner",
        prompt="Plan the auth feature.",
        teammate_name="helper-1",
    )

    assert result.pane_id.startswith("%")
    assert result.teammate_name == "helper-1"
    assert result.persona == "planner"
    assert result.cli == "claude"

    calls = psmux_backend.recorded_calls
    split = next(c for c in calls if "split-window" in c.args)
    assert "claude" in " ".join(split.args)

    send = next(c for c in calls if "send-keys" in c.args)
    keys_arg = send.args[send.args.index("-l") + 1]
    assert "You are the Planner teammate" in keys_arg
    assert "Plan the auth feature." in keys_arg

    assert len(runner.recorded_spawns) == 1
    assert runner.recorded_spawns[0].persona == "planner"


def test_spawn_mock_uses_safe_command_and_skips_send_keys(
    mock_runner: TeammateRunner,
    psmux_backend: PsmuxBackend,
) -> None:
    result = mock_runner.spawn(
        psmux_session="test",
        persona="planner",
        prompt="ignored in mock",
        teammate_name="helper-1",
    )

    assert result.pane_id.startswith("%")
    calls = psmux_backend.recorded_calls
    split = next(c for c in calls if "split-window" in c.args)
    joined = " ".join(split.args)
    assert "claude" not in joined
    assert "dry-run teammate ready" in joined
    assert not any("send-keys" in c.args for c in calls)


def test_spawn_unknown_persona_raises(runner: TeammateRunner) -> None:
    with pytest.raises(PersonaNotFoundError):
        runner.spawn(
            psmux_session="test",
            persona="ghost",
            prompt="x",
            teammate_name="helper-1",
        )


def test_spawn_passes_cwd(
    runner: TeammateRunner,
    psmux_backend: PsmuxBackend,
    tmp_path: Path,
) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    runner.spawn(
        psmux_session="test",
        persona="planner",
        prompt="x",
        teammate_name="helper-1",
        cwd=project,
    )
    split = next(c for c in psmux_backend.recorded_calls if "split-window" in c.args)
    assert split.cwd == str(project.resolve())
