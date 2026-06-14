"""TUI refresh integration (no watchfiles thread)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from agent_team.mailbox import send
from agent_team.session import Member, SessionStore
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


def test_refresh_updates_header_teammate_count(
    tui_context: TuiContext, session_store: SessionStore
) -> None:
    """A teammate added after mount must move the header counter on refresh.

    Regression: the count was computed once in on_mount and never recomputed,
    so the header stayed frozen (e.g. 0/3) even as teammates spawned.
    """

    async def run() -> None:
        watcher = MagicMock()
        async with AgentTeamApp(tui_context, watcher=watcher).run_test() as pilot:
            await pilot.pause()
            # Fixture session starts with one teammate (helper-1).
            assert "1/5 teammates" in pilot.app.sub_title

            session = session_store.load(tui_context.session_id)
            session.members.append(
                Member(
                    name="helper-2",
                    role="teammate",
                    persona="implementer",
                    cli="claude",
                    pane_id="%2",
                    backend="psmux",
                    status="running",
                )
            )
            session_store.update_members(tui_context.session_id, session.members)

            refresh_all_panels(pilot.app)
            assert "2/5 teammates" in pilot.app.sub_title

    asyncio.run(run())
