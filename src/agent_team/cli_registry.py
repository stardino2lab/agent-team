"""CLI capability registry.

Leaf module — does NOT import other agent_team modules. Owns the single source
of truth for which CLIs the orchestrator recognises and what each one can do.

Currently registered: claude (lead + teammate), codex (teammate only).
antigravity is planned for S11+ and is intentionally NOT registered yet;
adding it here without the matching lead launch builder / persona YAML would
leave a dead spawn path.
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

    def __post_init__(self) -> None:
        if self.supports_lead and not self.mcp_config_filename:
            raise ValueError(
                f"{self.name}: supports_lead=True requires mcp_config_filename"
            )
        if not (self.supports_lead or self.supports_teammate):
            raise ValueError(f"{self.name}: must support at least one role")


_REGISTRY: dict[str, CliSpec] = {
    "claude": CliSpec(
        name="claude",
        supports_lead=True,
        supports_teammate=True,
        mcp_config_filename="claude-mcp.json",
    ),
    "codex": CliSpec(
        name="codex",
        supports_lead=False,
        supports_teammate=True,
        mcp_config_filename=None,
    ),
    # antigravity: S11 — added together with persona YAML + lead launch builder.
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
