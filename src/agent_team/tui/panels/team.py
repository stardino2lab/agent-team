"""Team panel."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Static

from agent_team.tui.context import TuiContext
from agent_team.tui.loaders import load_member_rows


class TeamPanel(Vertical):
    """Read-only session members view."""

    def compose(self):
        yield Static("Team", classes="panel-title")
        yield Static("", id="team-body")

    def refresh_panel(self, ctx: TuiContext) -> None:
        session = ctx.store.load(ctx.session_id)
        rows = load_member_rows(session)
        lines = []
        for row in rows:
            pane = row.pane_id or "—"
            persona = row.persona or "—"
            lines.append(f"{row.name} ({row.role}, {row.cli}, {persona}) pane {pane}")
        self.query_one("#team-body", Static).update("\n".join(lines) if lines else "(empty)")
