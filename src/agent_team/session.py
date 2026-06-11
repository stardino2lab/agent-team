"""Session metadata persistence."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agent_team._io import format_ts, read_json, safe_segment, utc_now, write_json


class SessionNotFoundError(FileNotFoundError):
    """Raised when session.json does not exist."""


class SessionExistsError(FileExistsError):
    """Raised when creating a session that already exists."""


@dataclass
class Member:
    name: str
    role: Literal["lead", "teammate"]
    persona: str | None
    cli: str
    pane_id: str | None
    backend: str
    status: str


@dataclass
class Session:
    session_id: str
    project_path: str
    psmux_session: str
    playbook: str | None
    playbook_mode: str
    created_at: str
    status: str
    members: list[Member]
    max_teammates: int


def default_base_dir() -> Path:
    home = os.environ.get("AGENT_TEAM_HOME")
    if home:
        return Path(home)
    return Path.home() / ".agent-team"


def _member_to_dict(member: Member) -> dict:
    return {
        "name": member.name,
        "role": member.role,
        "persona": member.persona,
        "cli": member.cli,
        "pane_id": member.pane_id,
        "backend": member.backend,
        "status": member.status,
    }


def _member_from_dict(data: dict) -> Member:
    return Member(
        name=data["name"],
        role=data["role"],
        persona=data.get("persona"),
        cli=data["cli"],
        pane_id=data.get("pane_id"),
        backend=data["backend"],
        status=data["status"],
    )


def _session_to_dict(session: Session) -> dict:
    return {
        "session_id": session.session_id,
        "project_path": session.project_path,
        "psmux_session": session.psmux_session,
        "playbook": session.playbook,
        "playbook_mode": session.playbook_mode,
        "created_at": session.created_at,
        "status": session.status,
        "members": [_member_to_dict(m) for m in session.members],
        "max_teammates": session.max_teammates,
    }


def _session_from_dict(data: dict) -> Session:
    return Session(
        session_id=data["session_id"],
        project_path=data["project_path"],
        psmux_session=data["psmux_session"],
        playbook=data.get("playbook"),
        playbook_mode=data["playbook_mode"],
        created_at=data["created_at"],
        status=data["status"],
        members=[_member_from_dict(m) for m in data["members"]],
        max_teammates=data["max_teammates"],
    )


class SessionStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or default_base_dir()

    def session_dir(self, session_id: str) -> Path:
        safe_segment(session_id, "session_id")
        return self.base_dir / "sessions" / session_id

    def ensure_layout(self, session_id: str) -> Path:
        session_dir = self.session_dir(session_id)
        (session_dir / "mailbox").mkdir(parents=True, exist_ok=True)
        (session_dir / "tasks").mkdir(parents=True, exist_ok=True)
        (session_dir / "approval").mkdir(parents=True, exist_ok=True)
        return session_dir

    def create(
        self,
        *,
        session_id: str,
        project_path: str,
        psmux_session: str,
        playbook: str | None = None,
        playbook_mode: str = "guide",
        members: list[Member] | None = None,
        max_teammates: int = 5,
        status: str = "active",
    ) -> Session:
        session_dir = self.ensure_layout(session_id)
        session_path = session_dir / "session.json"
        if session_path.exists():
            raise SessionExistsError(f"Session already exists: {session_id}")

        session = Session(
            session_id=session_id,
            project_path=project_path,
            psmux_session=psmux_session,
            playbook=playbook,
            playbook_mode=playbook_mode,
            created_at=format_ts(utc_now()),
            status=status,
            members=members or [],
            max_teammates=max_teammates,
        )
        write_json(session_path, _session_to_dict(session))
        return session

    def load(self, session_id: str) -> Session:
        session_path = self.session_dir(session_id) / "session.json"
        if not session_path.exists():
            raise SessionNotFoundError(f"Session not found: {session_id}")
        return _session_from_dict(read_json(session_path))

    def save(self, session: Session) -> None:
        session_path = self.session_dir(session.session_id) / "session.json"
        write_json(session_path, _session_to_dict(session))

    def update_members(self, session_id: str, members: list[Member]) -> Session:
        session = self.load(session_id)
        session.members = members
        self.save(session)
        return session
