"""Module entry: python -m agent_team.tui"""

from __future__ import annotations

import sys

from agent_team.session import SessionNotFoundError
from agent_team.tui.app import AgentTeamApp
from agent_team.tui.context import TuiConfigError, resolve_tui_context


def main() -> None:
    try:
        ctx = resolve_tui_context()
    except TuiConfigError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionNotFoundError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc

    AgentTeamApp(ctx).run()


if __name__ == "__main__":
    main()
