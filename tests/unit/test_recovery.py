"""recovery.py: spawn retry records (S14b)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from agent_team._io import utc_now
from agent_team.recovery import (
    attempts_for,
    backoff,
    clear_retry,
    read_retries,
    record_retry,
)


def test_backoff_capped() -> None:
    assert backoff(1) == 5.0
    assert backoff(2) == 20.0
    assert backoff(3) == 60.0
    assert backoff(9) == 60.0  # capped
    assert backoff(0) == 5.0


def test_record_read_round_trip(tmp_path: Path) -> None:
    record_retry(
        tmp_path, request_id="apr-1", attempts=1,
        next_eligible=utc_now() + timedelta(seconds=5), last_error="boom",
    )
    retries = read_retries(tmp_path)
    assert retries["apr-1"].attempts == 1
    assert retries["apr-1"].last_error == "boom"
    assert attempts_for(tmp_path, "apr-1") == 1
    assert attempts_for(tmp_path, "nope") == 0


def test_latest_record_wins(tmp_path: Path) -> None:
    now = utc_now()
    record_retry(tmp_path, request_id="apr-1", attempts=1, next_eligible=now, last_error="a")
    record_retry(tmp_path, request_id="apr-1", attempts=2, next_eligible=now, last_error="b")
    assert read_retries(tmp_path)["apr-1"].attempts == 2


def test_clear_tombstones_record(tmp_path: Path) -> None:
    record_retry(tmp_path, request_id="apr-1", attempts=1, next_eligible=utc_now(), last_error="x")
    clear_retry(tmp_path, "apr-1")
    assert "apr-1" not in read_retries(tmp_path)


def test_clear_noop_when_no_file(tmp_path: Path) -> None:
    clear_retry(tmp_path, "apr-1")  # must not create the file or raise
    assert read_retries(tmp_path) == {}


def test_read_tolerates_torn_trailing_line(tmp_path: Path) -> None:
    record_retry(tmp_path, request_id="apr-1", attempts=1, next_eligible=utc_now(), last_error="x")
    path = tmp_path / "recovery" / "retries.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write('{"request_id": "apr-2", "att')  # torn mid-write
    # apr-1 still readable; torn apr-2 line skipped.
    assert "apr-1" in read_retries(tmp_path)
