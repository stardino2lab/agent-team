"""Textual TUI application."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from agent_team.tui.context import TuiContext
from agent_team.tui.modal import SpawnApprovalModal
from agent_team.tui.panels import LogPanel, MailPanel, TasksPanel, TeamPanel
from agent_team.tui.watcher import SessionWatcher


class HelpScreen(Screen):
    """Keyboard help overlay."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        yield Static(
            "Tab: next panel\n"
            "F5: refresh\n"
            "? : help\n"
            "When spawn modal is open: Y approve, N deny\n",
            id="help-text",
        )


class AgentTeamApp(App):
    """Four-panel session observer with spawn approval modal."""

    CSS = """
    Grid {
        grid-size: 2 2;
        grid-gutter: 1;
        height: 1fr;
    }
    .panel-title {
        text-style: bold;
        color: $accent;
    }
    #modal-title {
        text-style: bold;
        color: $warning;
    }
    """

    BINDINGS = [
        Binding("f5", "refresh", "Refresh"),
        Binding("tab", "focus_next", "Next panel"),
        Binding("question_mark", "help", "Help"),
    ]

    def __init__(
        self,
        ctx: TuiContext,
        watcher: SessionWatcher | None = None,
    ) -> None:
        super().__init__()
        self.ctx = ctx
        self._watcher = watcher
        self._started_watcher = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Grid():
            yield MailPanel(id="mail-panel")
            yield TasksPanel(id="tasks-panel")
            yield TeamPanel(id="team-panel")
            yield LogPanel(id="log-panel")
        yield Footer()

    def on_mount(self) -> None:
        session = self.ctx.store.load(self.ctx.session_id)
        teammate_count = sum(1 for m in session.members if m.role == "teammate")
        max_t = session.max_teammates
        self.sub_title = f"{self.ctx.session_id} · {teammate_count}/{max_t} teammates"
        refresh_all_panels(self)
        if self._watcher is None:
            self._watcher = SessionWatcher(
                self.ctx.session_dir,
                lambda: self.call_from_thread(refresh_all_panels, self),
            )
        if not self._started_watcher:
            self._watcher.start()
            self._started_watcher = True

    def on_unmount(self) -> None:
        if self._watcher is not None:
            self._watcher.stop()

    @property
    def mail(self) -> MailPanel:
        return self.query_one("#mail-panel", MailPanel)

    @property
    def tasks(self) -> TasksPanel:
        return self.query_one("#tasks-panel", TasksPanel)

    @property
    def team(self) -> TeamPanel:
        return self.query_one("#team-panel", TeamPanel)

    @property
    def log_panel(self) -> LogPanel:
        return self.query_one("#log-panel", LogPanel)

    def action_refresh(self) -> None:
        refresh_all_panels(self)

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def check_spawn_modal(self) -> None:
        pending = self.ctx.approval.get_pending(self.ctx.session_dir)
        current = self.screen if isinstance(self.screen, SpawnApprovalModal) else None
        current_id = current.pending.request_id if current else None
        pending_id = pending.request_id if pending else None
        if current_id == pending_id:
            return
        if current is not None:
            self.pop_screen()
        if pending is not None:
            self.push_screen(SpawnApprovalModal(self.ctx, pending, self))


def refresh_all_panels(app: AgentTeamApp) -> None:
    ctx = app.ctx
    app.mail.refresh_panel(ctx.session_dir)
    app.tasks.refresh_panel(ctx.session_dir)
    app.team.refresh_panel(ctx)
    app.log_panel.refresh_panel(ctx.session_dir)
    app.check_spawn_modal()
