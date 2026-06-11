"""TUI refresh integration (no watchfiles thread)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from agent_team.mailbox import send
from agent_team.tui.app import AgentTeamApp, refresh_all_panels
from agent_team.tui.context import TuiContext
from agent_team.tui.loaders import load_mail_rows


def test_refresh_all_panels_picks_up_new_mail(tui_context: TuiContext) -> None:
    async def run() -> None:
        watcher = MagicMock()
        async with AgentTeamApp(tui_context, watcher=watcher).run_test() as pilot:
            await pilot.pause()
            before = len(load_mail_rows(tui_context.session_dir))
            send(tui_context.session_dir, from_="lead", to="helper-1", body="refresh me")
            refresh_all_panels(pilot.app)
            after = len(load_mail_rows(tui_context.session_dir))
            assert after == before + 1
            body = pilot.app.mail.query_one("#mail-body").content
            assert "refresh me" in str(body)

    asyncio.run(run())
