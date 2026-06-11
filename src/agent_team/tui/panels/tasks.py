"""Tasks panel."""

from __future__ import annotations

from pathlib import Path

from textual.containers import Vertical
from textual.widgets import Static

from agent_team.tui.loaders import load_task_rows


class TasksPanel(Vertical):
    """Read-only task board view."""

    def compose(self):
        yield Static("Tasks", classes="panel-title")
        yield Static("", id="tasks-body")

    def refresh_panel(self, session_dir: Path) -> None:
        rows = load_task_rows(session_dir)
        lines = []
        for row in rows:
            assignee = row.assignee or "unassigned"
            lines.append(f"{row.task_id} [{row.state}] {row.title} ({assignee})")
        self.query_one("#tasks-body", Static).update("\n".join(lines) if lines else "(empty)")
