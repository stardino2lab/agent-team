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
