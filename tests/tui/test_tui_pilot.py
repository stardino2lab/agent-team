"""Textual pilot tests (headless App.run_test)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from textual.widgets import Label, Static

from agent_team.tui.app import AgentTeamApp
from agent_team.tui.context import TuiContext
from agent_team.tui.modal import SpawnApprovalModal
from agent_team.tui.panels import MailPanel


def test_pilot_shows_mail_panel_header(tui_context: TuiContext) -> None:
    async def run() -> None:
        watcher = MagicMock()
        async with AgentTeamApp(tui_context, watcher=watcher).run_test() as pilot:
            await pilot.pause()
            mail = pilot.app.query_one("#mail-panel", MailPanel)
            title = mail.query_one(".panel-title", Static)
            assert str(title.content) == "Mail"

    asyncio.run(run())


def test_pilot_shows_spawn_modal_when_pending(tui_context: TuiContext) -> None:
    tui_context.approval.request_spawn(
        tui_context.session_dir,
        persona="planner",
        cli="claude",
        prompt="Need help",
        requested_by="lead",
        event_log=tui_context.event_log,
    )

    async def run() -> None:
        watcher = MagicMock()
        async with AgentTeamApp(tui_context, watcher=watcher).run_test() as pilot:
            await pilot.pause()
            assert isinstance(pilot.app.screen, SpawnApprovalModal)
            title = pilot.app.screen.query_one("#modal-title", Label)
            assert str(title.content) == "Spawn approval"

    asyncio.run(run())
