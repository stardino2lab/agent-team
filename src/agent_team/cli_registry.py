"""CLI capability registry.

Leaf module — does NOT import other agent_team modules. Owns the single source
of truth for which CLIs the orchestrator recognises and what each one can do.

Currently registered: claude (lead + teammate), codex (lead + teammate),
agy (Antigravity, teammate only — lead deferred: agy has no MCP subcommand,
so it cannot yet host the agent-team MCP server). gemini was superseded by agy.
"""

from __future__ import annotations

from dataclasses import dataclass


class UnknownCliError(ValueError):
    """Raised when a CLI name is not in the registry."""


class LeadCliNotSupportedError(ValueError):
    """Raised when a CLI is registered but lacks lead support."""


@dataclass(frozen=True)
class CliSpec:
    name: str
    supports_lead: bool
    supports_teammate: bool
    mcp_config_filename: str | None
    # Per-CLI args the RUNNER appends to a teammate's bare launch command (read
    # from here, never from the lead — preserves lead/teammate CLI decoupling).
    # codex: run non-interactively (no per-command approval, no sandbox, no trust
    # prompt) so a teammate pane works hands-off. claude: none (bare launch).
    teammate_launch_args: tuple[str, ...] = ()
    # How the lead MCP config is delivered: "json" (a file passed via
    # --mcp-config, claude) or "toml" (a CODEX_HOME profile loaded via --profile,
    # codex). Required for any lead-capable CLI.
    mcp_format: str | None = None

    def __post_init__(self) -> None:
        if self.supports_lead and not self.mcp_format:
            raise ValueError(
                f"{self.name}: supports_lead=True requires mcp_format"
            )
        if self.mcp_format == "json" and not self.mcp_config_filename:
            raise ValueError(
                f"{self.name}: mcp_format='json' requires mcp_config_filename"
            )
        if not (self.supports_lead or self.supports_teammate):
            raise ValueError(f"{self.name}: must support at least one role")


_REGISTRY: dict[str, CliSpec] = {
    "claude": CliSpec(
        name="claude",
        supports_lead=True,
        supports_teammate=True,
        mcp_config_filename="claude-mcp.json",
        mcp_format="json",
    ),
    "codex": CliSpec(
        name="codex",
        supports_lead=True,
        supports_teammate=True,
        mcp_config_filename=None,
        teammate_launch_args=("--dangerously-bypass-approvals-and-sandbox",),
        mcp_format="toml",
    ),
    "agy": CliSpec(
        name="agy",
        supports_lead=False,  # lead deferred: agy has no MCP subcommand
        supports_teammate=True,
        mcp_config_filename=None,
        # agy is Claude-Code-derived: the teammate runs INTERACTIVELY in its pane
        # and gets the send_keys kickoff, so this is the interactive auto-approve
        # flag (NOT -p/--print, which is headless single-shot and would exit before
        # the kickoff). One flag auto-approves all tool permission requests.
        # Confirmed present in `agy --help`. Pending live G1 — see
        # tests/manual/s12-agy-gates.md.
        teammate_launch_args=("--dangerously-skip-permissions",),
        mcp_format=None,
    ),
}


def get_cli_spec(name: str) -> CliSpec:
    spec = _REGISTRY.get(name)
    if spec is None:
        raise UnknownCliError(f"Unknown CLI: {name!r}")
    return spec


def is_teammate_supported(name: str) -> bool:
    spec = _REGISTRY.get(name)
    return spec is not None and spec.supports_teammate


def is_lead_supported(name: str) -> bool:
    spec = _REGISTRY.get(name)
    return spec is not None and spec.supports_lead
