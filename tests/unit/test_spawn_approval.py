"""Spawn approval unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_team._io import InvalidPathSegmentError
from agent_team.event_log import EventLog
from agent_team.spawn_approval import (
    SpawnApproval,
    SpawnPendingError,
    SpawnRequestMismatchError,
    SpawnRequestNotFoundError,
)


@pytest.fixture
def approval() -> SpawnApproval:
    return SpawnApproval()


def test_request_spawn_writes_pending_and_event(
    session_dir: Path, approval: SpawnApproval, event_log: EventLog
) -> None:
    request = approval.request_spawn(
        session_dir,
        persona="planner",
        cli="claude",
        prompt="Plan the feature",
        requested_by="lead",
        teammate_name="planner-1",
        event_log=event_log,
    )
    assert request.request_id == "apr-001"
    assert request.status == "pending"
    assert (session_dir / "approval" / "pending.json").exists()

    pending = approval.get_pending(session_dir)
    assert pending is not None
    assert pending.persona == "planner"
    assert pending.teammate_name == "planner-1"

    events = event_log.read(session_dir)
    assert len(events) == 1
    assert events[0].type == "spawn_requested"
    assert events[0].payload == {
        "request_id": "apr-001",
        "persona": "planner",
        "cli": "claude",
        "requested_by": "lead",
    }


def test_get_pending_none_after_approve(
    session_dir: Path, approval: SpawnApproval, event_log: EventLog
) -> None:
    req = approval.request_spawn(
        session_dir,
        persona="planner",
        cli="claude",
        prompt="x",
        requested_by="lead",
    )
    assert approval.get_pending(session_dir) is not None
    approval.approve(session_dir, req.request_id, event_log=event_log)
    assert approval.get_pending(session_dir) is None


def test_second_request_raises_pending_error(session_dir: Path, approval: SpawnApproval) -> None:
    approval.request_spawn(
        session_dir,
        persona="planner",
        cli="claude",
        prompt="one",
        requested_by="lead",
    )
    with pytest.raises(SpawnPendingError):
        approval.request_spawn(
            session_dir,
            persona="reviewer",
            cli="claude",
            prompt="two",
            requested_by="lead",
        )


def test_approve_resolution_snapshot_and_event(
    session_dir: Path, approval: SpawnApproval, event_log: EventLog
) -> None:
    req = approval.request_spawn(
        session_dir,
        persona="implementer",
        cli="codex",
        prompt="Build API",
        requested_by="lead",
        teammate_name="impl-1",
        event_log=event_log,
    )
    resolution = approval.approve(
        session_dir,
        req.request_id,
        decided_by="test",
        event_log=event_log,
    )
    assert resolution.decision == "approved"
    assert resolution.persona == "implementer"
    assert resolution.cli == "codex"
    assert resolution.prompt == "Build API"
    assert resolution.teammate_name == "impl-1"
    assert resolution.requested_by == "lead"
    assert not (session_dir / "approval" / "pending.json").exists()

    events = event_log.read(session_dir)
    assert events[-1].type == "spawn_approved"
    assert events[-1].payload == {"request_id": "apr-001", "persona": "implementer"}


def test_deny_minimal_resolution(
    session_dir: Path, approval: SpawnApproval, event_log: EventLog
) -> None:
    req = approval.request_spawn(
        session_dir,
        persona="planner",
        cli="claude",
        prompt="x",
        requested_by="lead",
        event_log=event_log,
    )
    resolution = approval.deny(session_dir, req.request_id, decided_by="test", event_log=event_log)
    assert resolution.decision == "denied"
    assert resolution.persona is None
    assert resolution.cli is None
    assert resolution.prompt is None
    assert resolution.teammate_name is None
    assert resolution.requested_by is None
    assert not (session_dir / "approval" / "pending.json").exists()

    events = event_log.read(session_dir)
    assert events[-1].type == "spawn_denied"
    assert events[-1].payload == {"request_id": "apr-001"}


def test_request_id_mismatch_on_approve_and_deny(
    session_dir: Path, approval: SpawnApproval
) -> None:
    approval.request_spawn(
        session_dir,
        persona="planner",
        cli="claude",
        prompt="x",
        requested_by="lead",
    )
    with pytest.raises(SpawnRequestMismatchError):
        approval.approve(session_dir, "apr-999")
    with pytest.raises(SpawnRequestMismatchError):
        approval.deny(session_dir, "apr-999")


def test_approve_without_pending(session_dir: Path, approval: SpawnApproval) -> None:
    with pytest.raises(SpawnRequestNotFoundError):
        approval.approve(session_dir, "apr-001")


def test_deny_without_pending(session_dir: Path, approval: SpawnApproval) -> None:
    with pytest.raises(SpawnRequestNotFoundError):
        approval.deny(session_dir, "apr-001")


def test_read_resolutions_multiple_lines(session_dir: Path, approval: SpawnApproval) -> None:
    first = approval.request_spawn(
        session_dir,
        persona="planner",
        cli="claude",
        prompt="a",
        requested_by="lead",
    )
    approval.approve(session_dir, first.request_id)
    second = approval.request_spawn(
        session_dir,
        persona="reviewer",
        cli="claude",
        prompt="b",
        requested_by="lead",
    )
    approval.deny(session_dir, second.request_id)

    resolutions = approval.read_resolutions(session_dir)
    assert len(resolutions) == 2
    assert resolutions[0].decision == "approved"
    assert resolutions[0].cli == "claude"
    assert resolutions[0].prompt == "a"
    assert resolutions[1].decision == "denied"
    assert resolutions[1].cli is None


def test_read_resolutions_and_next_request_id(
    session_dir: Path, approval: SpawnApproval
) -> None:
    first = approval.request_spawn(
        session_dir,
        persona="planner",
        cli="claude",
        prompt="a",
        requested_by="lead",
    )
    approval.approve(session_dir, first.request_id)
    second = approval.request_spawn(
        session_dir,
        persona="reviewer",
        cli="claude",
        prompt="b",
        requested_by="lead",
    )
    assert second.request_id == "apr-002"

    resolutions = approval.read_resolutions(session_dir)
    assert len(resolutions) == 1
    assert resolutions[0].decision == "approved"
    assert resolutions[0].persona == "planner"
    assert resolutions[0].prompt == "a"


def test_safe_segment_rejects_bad_persona(session_dir: Path, approval: SpawnApproval) -> None:
    with pytest.raises(InvalidPathSegmentError):
        approval.request_spawn(
            session_dir,
            persona="../evil",
            cli="claude",
            prompt="x",
            requested_by="lead",
        )


def test_safe_segment_rejects_bad_requester(session_dir: Path, approval: SpawnApproval) -> None:
    with pytest.raises(InvalidPathSegmentError):
        approval.request_spawn(
            session_dir,
            persona="planner",
            cli="claude",
            prompt="x",
            requested_by="../evil",
        )


def test_tampered_pending_rejected_on_load(session_dir: Path, approval: SpawnApproval) -> None:
    approval.request_spawn(
        session_dir,
        persona="planner",
        cli="claude",
        prompt="x",
        requested_by="lead",
    )
    pending_path = session_dir / "approval" / "pending.json"
    pending_path.write_text(
        pending_path.read_text(encoding="utf-8").replace('"planner"', '"../evil"'),
        encoding="utf-8",
    )
    with pytest.raises(InvalidPathSegmentError):
        approval.get_pending(session_dir)


def test_invalid_cli_rejected(session_dir: Path, approval: SpawnApproval) -> None:
    with pytest.raises(ValueError, match="Invalid cli"):
        approval.request_spawn(
            session_dir,
            persona="planner",
            cli="gpt",
            prompt="x",
            requested_by="lead",
        )


def test_prompt_preview_truncated(session_dir: Path, approval: SpawnApproval) -> None:
    long_prompt = "x" * 250
    request = approval.request_spawn(
        session_dir,
        persona="planner",
        cli="claude",
        prompt=long_prompt,
        requested_by="lead",
    )
    assert len(request.prompt_preview) == 200
    assert request.prompt_preview == long_prompt[:200]
    assert request.prompt == long_prompt


def test_request_spawn_without_event_log(session_dir: Path, approval: SpawnApproval) -> None:
    approval.request_spawn(
        session_dir,
        persona="planner",
        cli="claude",
        prompt="quiet",
        requested_by="lead",
    )
    assert not (session_dir / "events.jsonl").exists()
