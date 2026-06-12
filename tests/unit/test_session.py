"""SessionStore unit tests."""

from __future__ import annotations

import pytest

from agent_team._io import InvalidPathSegmentError
from agent_team.session import (
    Member,
    SessionExistsError,
    SessionLoadError,
    SessionNotFoundError,
    SessionStore,
)


def test_create_session_layout_and_file(session_store: SessionStore) -> None:
    session = session_store.create(
        session_id="s1-test",
        project_path="c:\\DEV\\payment-api",
        psmux_session="s1-test",
    )
    session_dir = session_store.session_dir("s1-test")

    assert (session_dir / "session.json").exists()
    assert (session_dir / "mailbox").is_dir()
    assert (session_dir / "tasks").is_dir()
    assert (session_dir / "approval").is_dir()
    assert session.playbook_mode == "guide"
    assert session.max_teammates == 5


def test_load_round_trip_members(session_store: SessionStore) -> None:
    members = [
        Member(
            name="lead",
            role="lead",
            persona=None,
            cli="claude",
            pane_id="%0",
            backend="psmux",
            status="running",
        ),
        Member(
            name="planner-1",
            role="teammate",
            persona="planner",
            cli="claude",
            pane_id="%2",
            backend="psmux",
            status="running",
        ),
    ]
    session_store.create(
        session_id="round-trip",
        project_path="c:\\DEV\\test",
        psmux_session="round-trip",
        members=members,
    )

    loaded = session_store.load("round-trip")
    assert len(loaded.members) == 2
    assert loaded.members[1].persona == "planner"
    assert loaded.members[1].pane_id == "%2"


def test_create_duplicate_raises(session_store: SessionStore) -> None:
    session_store.create(
        session_id="dup",
        project_path="c:\\DEV\\test",
        psmux_session="dup",
    )
    with pytest.raises(SessionExistsError):
        session_store.create(
            session_id="dup",
            project_path="c:\\DEV\\test",
            psmux_session="dup",
        )


def test_invalid_session_id_rejected(session_store: SessionStore) -> None:
    with pytest.raises(InvalidPathSegmentError):
        session_store.session_dir("../escape")


def test_load_missing_raises(session_store: SessionStore) -> None:
    with pytest.raises(SessionNotFoundError):
        session_store.load("never-existed")


def test_load_corrupt_raises(session_store: SessionStore) -> None:
    session_store.create(session_id="corrupt", project_path="x", psmux_session="corrupt")
    session_path = session_store.session_dir("corrupt") / "session.json"
    session_path.write_text("{ not valid json", encoding="utf-8")
    with pytest.raises(SessionLoadError):
        session_store.load("corrupt")
