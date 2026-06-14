"""payment-api E2E fixture (S10c): loadable config + E2E-correct persona CLIs.

The codex teammates (implementer, tester) launch via the same CLI-neutral path
as claude — there is no codex-specific launch code — so verifying the fixture +
persona routing is the substance of S10c.
"""

from __future__ import annotations

from pathlib import Path

from agent_team.cli_registry import is_teammate_supported
from agent_team.personas import PersonaRegistry
from agent_team.project_loader import ProjectLoader
from agent_team.psmux_backend import PsmuxBackend
from agent_team.teammate_runner import TeammateRunner

# tests/unit/<this file> -> parents[1] == tests/ -> tests/fixtures/payment-api
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "payment-api"


def test_payment_api_config_loads_with_team_personas() -> None:
    config = ProjectLoader(FIXTURE).load_config()
    assert config["project_name"] == "payment-api"
    assert config["lead_cli"] == "claude"
    assert config["allowed_personas"] == [
        "planner",
        "implementer",
        "tester",
        "reviewer",
    ]
    assert config["max_teammates"] >= 4  # room for the four E2E teammates


def test_payment_api_persona_clis_match_e2e(empty_global_personas: Path) -> None:
    registry = PersonaRegistry(project_path=FIXTURE, global_dir=empty_global_personas)
    expected = {
        "planner": "claude",
        "implementer": "codex",
        "tester": "codex",
        "reviewer": "claude",
    }
    for name, cli in expected.items():
        persona = registry.get(name)
        assert persona.cli == cli, f"{name} cli={persona.cli!r}, expected {cli!r}"
    # Both teammate CLIs go through the same registry-gated, CLI-neutral launch.
    assert is_teammate_supported("codex")
    assert is_teammate_supported("claude")


def test_payment_api_fixture_layout_present() -> None:
    assert (FIXTURE / "TEAM.md").exists()
    assert (FIXTURE / "src" / "payment_service.py").exists()
    assert (FIXTURE / "tests" / "test_payment.py").exists()
    assert (FIXTURE / ".agent-team" / "playbooks" / "new-feature.yaml").exists()


def test_codex_teammate_launches_cli_neutral_for_fixture(
    psmux_backend: PsmuxBackend,
    persona_registry: PersonaRegistry,
    tmp_path: Path,
) -> None:
    """The codex implementer launches via the bare CLI-neutral path — proving the
    S10c claim that codex needs no per-CLI launch code."""
    psmux_backend.new_session("pay")
    runner = TeammateRunner(psmux_backend, persona_registry, mock=False)
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    result = runner.spawn(
        psmux_session="pay",
        persona="implementer",  # cli=codex
        prompt="Add a refund API following the charge pattern.",
        teammate_name="impl-1",
        session_id="pay",
        session_dir=session_dir,
        project_path=FIXTURE,
    )

    assert result.cli == "codex"
    split = next(
        c for c in psmux_backend.recorded_calls if "split-window" in c.args
    )
    joined = " ".join(split.args)
    assert "codex" in joined
    # No per-CLI flags — same launch shape as a claude teammate.
    assert "--append-system-prompt" not in joined
    assert "--mcp-config" not in joined
    # Runs from the project root, like every teammate (S10a).
    assert split.cwd == str(FIXTURE.resolve())
