"""Event log panel."""

from __future__ import annotations

from pathlib import Path

from textual.containers import Vertical
from textual.widgets import Static

from agent_team.tui.loaders import load_event_rows


class LogPanel(Vertical):
    """Read-only event log tail."""

    def compose(self):
        yield Static("Event Log", classes="panel-title")
        yield Static("", id="log-body")

    def refresh_panel(self, session_dir: Path) -> None:
        rows = load_event_rows(session_dir)
        lines = [f"[{row.ts}] {row.summary}" for row in rows]
        self.query_one("#log-body", Static).update("\n".join(lines) if lines else "(empty)")
