"""Shared I/O helpers for session data files."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

_SAFE_SEGMENT = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


class InvalidPathSegmentError(ValueError):
    """Raised when a path segment contains unsafe characters."""


def safe_segment(name: str, label: str) -> str:
    if not name or not _SAFE_SEGMENT.match(name):
        raise InvalidPathSegmentError(f"Invalid {label}: {name!r}")
    return name


def utc_now() -> datetime:
    return datetime.now(UTC)


def format_ts(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def parse_since(since: datetime | str | None) -> datetime | None:
    if since is None:
        return None
    if isinstance(since, str):
        return parse_ts(since)
    if since.tzinfo is None:
        return since.replace(tzinfo=UTC)
    return since.astimezone(UTC)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
