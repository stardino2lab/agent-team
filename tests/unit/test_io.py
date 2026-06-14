"""_io helper unit tests."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from agent_team._io import (
    InvalidPathSegmentError,
    parse_since,
    read_json,
    safe_segment,
    write_json,
)


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


def test_write_json_round_trips_and_leaves_no_temp(tmp_path: Path) -> None:
    """write_json must commit via an atomic rename and leave no .tmp sibling.

    Regression: a plain write_text truncates in place, so a concurrent reader
    (the TUI refresh loop) could observe a half-written session.json.
    """
    p = tmp_path / "session.json"
    write_json(p, {"a": 1})
    assert read_json(p) == {"a": 1}
    assert not (tmp_path / "session.json.tmp").exists()
    assert list(tmp_path.iterdir()) == [p]

    # Overwriting an existing file is also atomic and leaves no temp behind.
    write_json(p, {"a": 2, "b": [1, 2, 3]})
    assert read_json(p) == {"a": 2, "b": [1, 2, 3]}
    assert not (tmp_path / "session.json.tmp").exists()
