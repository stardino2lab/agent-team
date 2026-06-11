"""Mail panel."""

from __future__ import annotations

from pathlib import Path

from textual.containers import Vertical
from textual.widgets import Static

from agent_team.tui.loaders import load_mail_rows


class MailPanel(Vertical):
    """Read-only merged mailbox view."""

    def compose(self):
        yield Static("Mail", classes="panel-title")
        yield Static("", id="mail-body")

    def refresh_panel(self, session_dir: Path) -> None:
        rows = load_mail_rows(session_dir)
        lines = [f"[{row.ts}] {row.from_} → {row.to}: {row.body}" for row in rows]
        self.query_one("#mail-body", Static).update("\n".join(lines) if lines else "(empty)")
