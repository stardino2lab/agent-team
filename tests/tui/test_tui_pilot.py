"""Textual pilot tests (headless App.run_test)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from textual.widgets import Label, Static

from agent_team.mailbox import send
from agent_team.tui.app import AgentTeamApp
from agent_team.tui.context import TuiContext
from agent_team.tui.modal import SpawnApprovalModal
from agent_team.tui.panels import LogPanel, MailPanel, TasksPanel, TeamPanel


def test_pilot_renders_all_four_panels(tui_context: TuiContext) -> None:
    async def run() -> None:
        watcher = MagicMock()
        async with AgentTeamApp(tui_context, watcher=watcher).run_test() as pilot:
            await pilot.pause()
            titles = {
                "mail": pilot.app.query_one("#mail-panel", MailPanel)
                .query_one(".panel-title", Static)
                .content,
                "tasks": pilot.app.query_one("#tasks-panel", TasksPanel)
                .query_one(".panel-title", Static)
                .content,
                "team": pilot.app.query_one("#team-panel", TeamPanel)
                .query_one(".panel-title", Static)
                .content,
                "log": pilot.app.query_one("#log-panel", LogPanel)
                .query_one(".panel-title", Static)
                .content,
            }
            assert str(titles["mail"]) == "Mail"
            assert str(titles["tasks"]) == "Tasks"
            assert str(titles["team"]) == "Team"
            assert str(titles["log"]) == "Event Log"

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


def test_pilot_approve_key_resolves_and_dismisses(tui_context: TuiContext) -> None:
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
            await pilot.press("y")
            await pilot.pause()
            assert not isinstance(pilot.app.screen, SpawnApprovalModal)
            # pending cleared
            assert (
                tui_context.approval.get_pending(tui_context.session_dir) is None
            )
            # log panel reflects spawn_approved
            log_body = pilot.app.query_one("#log-body", Static).content
            assert "spawn_approved" in str(log_body)

    asyncio.run(run())


def test_pilot_deny_key_resolves(tui_context: TuiContext) -> None:
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
            await pilot.press("n")
            await pilot.pause()
            assert not isinstance(pilot.app.screen, SpawnApprovalModal)
            assert (
                tui_context.approval.get_pending(tui_context.session_dir) is None
            )

    asyncio.run(run())


def test_pilot_f5_refresh_picks_up_new_mail(tui_context: TuiContext) -> None:
    async def run() -> None:
        watcher = MagicMock()
        async with AgentTeamApp(tui_context, watcher=watcher).run_test() as pilot:
            await pilot.pause()
            send(
                tui_context.session_dir,
                from_="lead",
                to="helper-1",
                body="ping after F5",
            )
            await pilot.press("f5")
            await pilot.pause()
            body = pilot.app.query_one("#mail-body", Static).content
            assert "ping after F5" in str(body)

    asyncio.run(run())


def test_pilot_modal_stays_open_after_unrelated_refresh(
    tui_context: TuiContext,
) -> None:
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
            # simulate watcher trigger via F5 while pending still set
            await pilot.press("f5")
            await pilot.pause()
            assert isinstance(pilot.app.screen, SpawnApprovalModal)

    asyncio.run(run())
