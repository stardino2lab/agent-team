"""_io helper unit tests."""

from __future__ import annotations

from datetime import datetime

import pytest

from agent_team._io import InvalidPathSegmentError, parse_since, safe_segment


def test_safe_segment_accepts_valid_names() -> None:
    assert safe_segment("test-session", "session_id") == "test-session"
    assert safe_segment("planner-1", "recipient") == "planner-1"
    assert safe_segment("task-001", "task_id") == "task-001"


@pytest.mark.parametrize(
    "value",
    ["../evil", "..", "a/b", r"a\b", "", "session with spaces"],
)
def test_safe_segment_rejects_unsafe(value: str) -> None:
    with pytest.raises(InvalidPathSegmentError):
        safe_segment(value, "session_id")


def test_parse_since_naive_datetime_treated_as_utc() -> None:
    naive = datetime(2026, 6, 10, 12, 0, 0)
    parsed = parse_since(naive)
    assert parsed is not None
    assert parsed.tzinfo is not None


def test_parse_since_iso_string() -> None:
    parsed = parse_since("2026-06-10T12:00:00Z")
    assert parsed is not None
    assert parsed.year == 2026
