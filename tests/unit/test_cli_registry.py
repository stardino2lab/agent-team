"""cli_registry unit tests."""

from __future__ import annotations

import pytest

from agent_team.cli_registry import (
    _REGISTRY,
    CliSpec,
    LeadCliNotSupportedError,
    UnknownCliError,
    get_cli_spec,
    is_lead_supported,
    is_teammate_supported,
)


@pytest.mark.parametrize("name,spec", list(_REGISTRY.items()))
def test_spec_invariant(name: str, spec: CliSpec) -> None:
    """Each registered entry satisfies the dataclass invariants.

    Adding a new CLI in _REGISTRY automatically gets these checks — keeps
    the registry honest as it grows.
    """
    assert spec.name == name
    if spec.supports_lead:
        assert spec.mcp_config_filename is not None
    else:
        assert spec.mcp_config_filename is None
    assert spec.supports_lead or spec.supports_teammate


def test_claude_is_registered_as_lead_and_teammate() -> None:
    spec = get_cli_spec("claude")
    assert spec.supports_lead is True
    assert spec.supports_teammate is True
    assert spec.mcp_config_filename == "claude-mcp.json"


def test_codex_is_teammate_only() -> None:
    spec = get_cli_spec("codex")
    assert spec.supports_lead is False
    assert spec.supports_teammate is True
    assert spec.mcp_config_filename is None


def test_antigravity_is_not_registered() -> None:
    """antigravity is S11 — must not be silently accepted."""
    with pytest.raises(UnknownCliError):
        get_cli_spec("antigravity")
    assert is_teammate_supported("antigravity") is False
    assert is_lead_supported("antigravity") is False


def test_get_cli_spec_unknown_raises() -> None:
    with pytest.raises(UnknownCliError, match="xyz"):
        get_cli_spec("xyz")


def test_is_teammate_supported_unknown_returns_false() -> None:
    assert is_teammate_supported("xyz") is False


def test_is_lead_supported_unknown_returns_false() -> None:
    assert is_lead_supported("xyz") is False


def test_post_init_rejects_lead_without_filename() -> None:
    with pytest.raises(ValueError, match="mcp_config_filename"):
        CliSpec(
            name="bogus",
            supports_lead=True,
            supports_teammate=False,
            mcp_config_filename=None,
        )


def test_post_init_rejects_no_role() -> None:
    with pytest.raises(ValueError, match="at least one role"):
        CliSpec(
            name="bogus",
            supports_lead=False,
            supports_teammate=False,
            mcp_config_filename=None,
        )


def test_lead_cli_not_supported_error_is_value_error() -> None:
    """Callers should be able to catch ValueError; we keep the hierarchy flat."""
    assert issubclass(LeadCliNotSupportedError, ValueError)
    assert issubclass(UnknownCliError, ValueError)


def test_codex_teammate_launch_args_bypass() -> None:
    from agent_team.cli_registry import get_cli_spec

    codex = get_cli_spec("codex")
    # D12: codex teammate runs hands-off (no per-command approval / sandbox /
    # trust prompts) — applied by the runner, never named by the lead.
    assert codex.teammate_launch_args == ("--dangerously-bypass-approvals-and-sandbox",)


def test_claude_teammate_launch_args_empty() -> None:
    from agent_team.cli_registry import get_cli_spec

    # claude teammate launches bare (CLI-neutral invariant; no per-CLI flags).
    assert get_cli_spec("claude").teammate_launch_args == ()
