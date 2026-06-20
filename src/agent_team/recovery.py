"""Spawn retry/recovery records (S14b).

Append-only `recovery/retries.jsonl` — deliberately OUTSIDE `approval/` so writing
a retry record does not self-wake the approval FileWatcher. Latest line per
request_id wins; a `cleared` tombstone drops it. Tolerates a torn trailing line.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from agent_team._io import format_ts

# Total spawn attempts before giving up (attempt 1 is the original spawn). With
# MAX=3: original fails -> retry (attempt 2) -> retry (attempt 3) -> terminal.
MAX_SPAWN_RETRIES = 3
_BACKOFF_S = [5.0, 20.0, 60.0]
_ERR_MAX = 500


def backoff(attempts: int) -> float:
    """Delay (seconds) before retry number `attempts` (1-based), capped."""
    if attempts < 1:
        return _BACKOFF_S[0]
    return _BACKOFF_S[min(attempts - 1, len(_BACKOFF_S) - 1)]


@dataclass
class RetryRecord:
    request_id: str
    attempts: int
    next_eligible_ts: str
    last_error: str


def _path(session_dir: Path) -> Path:
    return session_dir / "recovery" / "retries.jsonl"


def _append(session_dir: Path, data: dict) -> None:
    path = _path(session_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")


def record_retry(
    session_dir: Path,
    *,
    request_id: str,
    attempts: int,
    next_eligible: datetime,
    last_error: str,
) -> RetryRecord:
    rec = RetryRecord(
        request_id=request_id,
        attempts=attempts,
        next_eligible_ts=format_ts(next_eligible),
        last_error=last_error[:_ERR_MAX],
    )
    _append(
        session_dir,
        {
            "request_id": rec.request_id,
            "attempts": rec.attempts,
            "next_eligible_ts": rec.next_eligible_ts,
            "last_error": rec.last_error,
            "state": "pending",
        },
    )
    return rec


def clear_retry(session_dir: Path, request_id: str) -> None:
    if not _path(session_dir).exists():
        return
    _append(session_dir, {"request_id": request_id, "state": "cleared"})


def read_retries(session_dir: Path) -> dict[str, RetryRecord]:
    path = _path(session_dir)
    if not path.exists():
        return {}
    latest: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue  # tolerate a torn trailing line (crash mid-append)
        rid = data.get("request_id")
        if rid:
            latest[rid] = data
    out: dict[str, RetryRecord] = {}
    for rid, data in latest.items():
        if data.get("state") == "cleared":
            continue
        out[rid] = RetryRecord(
            request_id=rid,
            attempts=data["attempts"],
            next_eligible_ts=data["next_eligible_ts"],
            last_error=data.get("last_error", ""),
        )
    return out


def attempts_for(session_dir: Path, request_id: str) -> int:
    rec = read_retries(session_dir).get(request_id)
    return rec.attempts if rec else 0
