"""Spawn approval modal."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from agent_team.spawn_approval import SpawnRequest, SpawnRequestNotFoundError, SpawnResolution
from agent_team.tui.context import TuiContext

if TYPE_CHECKING:
    from agent_team.tui.app import AgentTeamApp


def handle_approve(ctx: TuiContext, request_id: str) -> SpawnResolution:
    return ctx.approval.approve(
        ctx.session_dir,
        request_id,
        decided_by="user",
        event_log=ctx.event_log,
    )


def handle_deny(ctx: TuiContext, request_id: str) -> SpawnResolution:
    return ctx.approval.deny(
        ctx.session_dir,
        request_id,
        decided_by="user",
        event_log=ctx.event_log,
    )


class SpawnApprovalModal(ModalScreen[None]):
    """Modal for approving or denying a spawn request."""

    BINDINGS = [
        ("y", "approve", "Approve"),
        ("n", "deny", "Deny"),
        Binding("escape", "noop", "", show=False),
    ]

    def __init__(self, ctx: TuiContext, pending: SpawnRequest, app: AgentTeamApp) -> None:
        super().__init__()
        self.ctx = ctx
        self.pending = pending
        self.team_app = app

    def compose(self) -> ComposeResult:
        session = self.ctx.store.load(self.ctx.session_id)
        teammate_count = sum(1 for m in session.members if m.role == "teammate")
        teammate_name = self.pending.teammate_name or "—"
        yield Vertical(
            Label("Spawn approval", id="modal-title"),
            Static(f"Persona: {self.pending.persona} ({self.pending.cli})"),
            Static(f"Teammate: {teammate_name}"),
            Static(f"Requested by: {self.pending.requested_by}"),
            Static(f"Teammates: {teammate_count} / {session.max_teammates}"),
            Static(self.pending.prompt_preview, id="preview"),
            Button("Approve (Y)", id="approve", variant="success"),
            Button("Deny (N)", id="deny", variant="error"),
            id="modal-root",
        )

    def action_approve(self) -> None:
        self._resolve(approve=True)

    def action_deny(self) -> None:
        self._resolve(approve=False)

    def action_noop(self) -> None:
        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "approve":
            self._resolve(approve=True)
        elif event.button.id == "deny":
            self._resolve(approve=False)

    def _resolve(self, *, approve: bool) -> None:
        try:
            if approve:
                handle_approve(self.ctx, self.pending.request_id)
            else:
                handle_deny(self.ctx, self.pending.request_id)
        except SpawnRequestNotFoundError as exc:
            self.notify(str(exc), severity="error")
            return

        # refresh_all_panels calls check_spawn_modal which pops this modal
        # now that pending is cleared. Do not also call dismiss() — that would
        # pop twice and raise ScreenStackError.
        from agent_team.tui.app import refresh_all_panels

        refresh_all_panels(self.team_app)
