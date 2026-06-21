"""cli_registry unit tests."""

from __future__ import annotations

import sys

import pytest

from agent_team.cli_registry import (
    _REGISTRY,
    CliSpec,
    LeadCliNotSupportedError,
    UnknownCliError,
    get_cli_spec,
    is_lead_supported,
    is_teammate_supported,
    resolve_teammate_submit_keys,
)


@pytest.mark.parametrize("name,spec", list(_REGISTRY.items()))
def test_spec_invariant(name: str, spec: CliSpec) -> None:
    """Each registered entry satisfies the dataclass invariants.

    Adding a new CLI in _REGISTRY automatically gets these checks — keeps
    the registry honest as it grows.
    """
    assert spec.name == name
    if spec.supports_lead:
        assert spec.mcp_format is not None
    if spec.mcp_format == "json":
        assert spec.mcp_config_filename is not None
    assert spec.supports_lead or spec.supports_teammate


def test_claude_is_registered_as_lead_and_teammate() -> None:
    spec = get_cli_spec("claude")
    assert spec.supports_lead is True
    assert spec.supports_teammate is True
    assert spec.mcp_config_filename == "claude-mcp.json"


def test_codex_is_lead_and_teammate() -> None:
    spec = get_cli_spec("codex")
    assert spec.supports_lead is True
    assert spec.supports_teammate is True
    assert spec.mcp_format == "toml"
    # codex delivers MCP inline via `-c` overrides, not a session-dir file.
    assert spec.mcp_config_filename is None


def test_antigravity_is_not_registered() -> None:
    """antigravity is S12 — must not be silently accepted."""
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
            mcp_format="json",
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


def test_codex_is_lead_capable_with_toml_format() -> None:
    from agent_team.cli_registry import get_cli_spec, is_lead_supported

    codex = get_cli_spec("codex")
    assert codex.supports_lead is True
    assert codex.mcp_format == "toml"
    # codex delivers MCP inline via `-c` overrides, not a session-dir file.
    assert codex.mcp_config_filename is None
    assert is_lead_supported("codex") is True


def test_claude_lead_uses_json_format() -> None:
    from agent_team.cli_registry import get_cli_spec

    claude = get_cli_spec("claude")
    assert claude.mcp_format == "json"
    assert claude.mcp_config_filename == "claude-mcp.json"


def test_cli_spec_lead_requires_mcp_format() -> None:
    from agent_team.cli_registry import CliSpec

    with pytest.raises(ValueError, match="mcp_format"):
        CliSpec(
            name="x",
            supports_lead=True,
            supports_teammate=False,
            mcp_config_filename=None,
            mcp_format=None,
        )


def test_codex_teammate_launch_args_bypass() -> None:
    from agent_team.cli_registry import get_cli_spec

    codex = get_cli_spec("codex")
    # D12: codex teammate runs hands-off (no per-command approval / sandbox /
    # trust prompts) — applied by the runner, never named by the lead. Exact-tuple
    # equality pins the COMPLETE launch-arg set (presence + order, no dup/stray arg);
    # the S14 update-nag pair is also asserted on its own below for intent.
    assert codex.teammate_launch_args == (
        "--dangerously-bypass-approvals-and-sandbox",
        "-c",
        "check_for_update_on_startup=false",
    )


def test_codex_teammate_launch_args_suppress_update_nag() -> None:
    from agent_team.cli_registry import get_cli_spec

    codex = get_cli_spec("codex")
    # S14 hardening: suppress codex's INTERACTIVE startup update-nag ("✨ Update
    # available! → 1. Update now"). Pre-fix, the readiness wait settled on the nag
    # and the kickoff Enter selected "Update now" → codex ran npm self-update and
    # the pane terminated with no teammate_ready (s11b §D11b Step B). A per-launch
    # `-c key=value` override (highest precedence over config.toml, parsed as a TOML
    # bool, no global file mutation) turns the startup check off at the root.
    assert codex.teammate_launch_args[-2:] == (
        "-c",
        "check_for_update_on_startup=false",
    )


def test_claude_teammate_launch_args_empty() -> None:
    from agent_team.cli_registry import get_cli_spec

    # claude teammate launches bare (CLI-neutral invariant; no per-CLI flags).
    assert get_cli_spec("claude").teammate_launch_args == ()


def test_default_teammate_submit_keys_are_enter() -> None:
    # Base (Windows psmux) submit keys: Enter alone. Verified live on Windows for
    # codex 0.139.0 (tmux 3.3.5): Enter alone submits (tests/manual/
    # s11b-teammate-hardening.md §D11b Step A).
    assert get_cli_spec("claude").teammate_submit_keys == ("Enter",)
    assert get_cli_spec("codex").teammate_submit_keys == ("Enter",)
    assert get_cli_spec("agy").teammate_submit_keys == ("Enter",)
    # POSIX (tmux/Linux) override: only codex declares Tab+Enter; the others fall
    # through to the base Enter on every platform.
    assert get_cli_spec("codex").teammate_submit_keys_posix == ("Tab", "Enter")
    assert get_cli_spec("claude").teammate_submit_keys_posix is None
    assert get_cli_spec("agy").teammate_submit_keys_posix is None


def test_resolve_submit_keys_default_is_platform_aware(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Without an env override, codex's default depends on the host: Windows psmux
    # submits on Enter; an off-Windows tmux pane needs Tab+Enter (the posix
    # override). claude has no posix override → Enter on both.
    monkeypatch.delenv("AGENT_TEAM_SUBMIT_KEYS_CODEX", raising=False)
    monkeypatch.delenv("AGENT_TEAM_SUBMIT_KEYS_CLAUDE", raising=False)

    monkeypatch.setattr(sys, "platform", "win32")
    assert resolve_teammate_submit_keys("codex") == ("Enter",)
    assert resolve_teammate_submit_keys("claude") == ("Enter",)

    monkeypatch.setattr(sys, "platform", "linux")
    assert resolve_teammate_submit_keys("codex") == ("Tab", "Enter")
    assert resolve_teammate_submit_keys("claude") == ("Enter",)


def test_resolve_submit_keys_env_override_wins_off_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The env var beats the posix default, so a Linux user can toggle codex back
    # to Enter (or anything) live without a code change.
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("AGENT_TEAM_SUBMIT_KEYS_CODEX", "Enter")
    assert resolve_teammate_submit_keys("codex") == ("Enter",)


def test_resolve_submit_keys_env_override_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Per-platform/per-version override without a code change: Linux codex needs
    # Tab+Enter, set via env while the Windows-verified default stays Enter.
    monkeypatch.setenv("AGENT_TEAM_SUBMIT_KEYS_CODEX", "Tab Enter")
    assert resolve_teammate_submit_keys("codex") == ("Tab", "Enter")
    monkeypatch.setenv("AGENT_TEAM_SUBMIT_KEYS_CLAUDE", "Tab Enter")
    assert resolve_teammate_submit_keys("claude") == ("Tab", "Enter")


def test_resolve_submit_keys_env_splits_on_whitespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_TEAM_SUBMIT_KEYS_CODEX", "  Tab   Enter  ")
    assert resolve_teammate_submit_keys("codex") == ("Tab", "Enter")


def test_resolve_submit_keys_empty_env_means_no_submit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Set-but-empty is an explicit "type without submitting" (the runner sends
    # no submit keypress) — distinct from unset (use the registry default).
    monkeypatch.setenv("AGENT_TEAM_SUBMIT_KEYS_CODEX", "")
    assert resolve_teammate_submit_keys("codex") == ()


def test_agy_registered_teammate_only() -> None:
    spec = get_cli_spec("agy")
    assert spec.supports_teammate is True
    assert spec.supports_lead is False  # lead deferred: no MCP subcommand
    assert spec.mcp_config_filename is None
    assert spec.mcp_format is None  # teammate-only needs no lead MCP format
    assert is_teammate_supported("agy") is True
    assert is_lead_supported("agy") is False


def test_agy_teammate_launch_args_are_interactive_auto_approve() -> None:
    spec = get_cli_spec("agy")
    # INTERACTIVE auto-approve (the teammate runs in a pane + receives the
    # send_keys kickoff) — NOT -p/--print (that is headless single-shot).
    # agy is Claude-Code-derived: one flag covers all tool approvals.
    assert spec.teammate_launch_args == ("--dangerously-skip-permissions",)
    assert "-p" not in spec.teammate_launch_args
    assert "--print" not in spec.teammate_launch_args
