"""Spawn approval queue for teammate requests."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agent_team._io import format_ts, read_json, safe_segment, utc_now, write_json
from agent_team.event_log import EventLog

_PREVIEW_LEN = 200
_APR_ID_PATTERN = re.compile(r"^apr-(\d+)$")
_VALID_CLI = frozenset({"claude", "codex"})


class SpawnPendingError(RuntimeError):
    """Raised when a spawn request is already pending."""


class SpawnRequestNotFoundError(LookupError):
    """Raised when no pending spawn request exists."""


class SpawnRequestMismatchError(ValueError):
    """Raised when request_id does not match the pending request."""


@dataclass
class SpawnRequest:
    request_id: str
    persona: str
    cli: str
    prompt: str
    prompt_preview: str
    teammate_name: str | None
    requested_by: str
    requested_at: str
    status: Literal["pending"] = "pending"


@dataclass
class SpawnResolution:
    request_id: str
    decision: Literal["approved", "denied"]
    decided_at: str
    decided_by: str
    persona: str | None = None
    cli: str | None = None
    prompt: str | None = None
    teammate_name: str | None = None
    requested_by: str | None = None


def _pending_path(session_dir: Path) -> Path:
    return session_dir / "approval" / "pending.json"


def _resolutions_path(session_dir: Path) -> Path:
    return session_dir / "approval" / "resolutions.jsonl"


def _make_preview(prompt: str, n: int = _PREVIEW_LEN) -> str:
    if len(prompt) <= n:
        return prompt
    return prompt[:n]


def _request_to_dict(request: SpawnRequest) -> dict:
    return {
        "request_id": request.request_id,
        "persona": request.persona,
        "cli": request.cli,
        "prompt": request.prompt,
        "prompt_preview": request.prompt_preview,
        "teammate_name": request.teammate_name,
        "requested_by": request.requested_by,
        "requested_at": request.requested_at,
        "status": request.status,
    }


def _request_from_dict(data: dict) -> SpawnRequest:
    return SpawnRequest(
        request_id=data["request_id"],
        persona=data["persona"],
        cli=data["cli"],
        prompt=data["prompt"],
        prompt_preview=data["prompt_preview"],
        teammate_name=data.get("teammate_name"),
        requested_by=data["requested_by"],
        requested_at=data["requested_at"],
        status=data.get("status", "pending"),
    )


def _resolution_to_dict(resolution: SpawnResolution) -> dict:
    data: dict = {
        "request_id": resolution.request_id,
        "decision": resolution.decision,
        "decided_at": resolution.decided_at,
        "decided_by": resolution.decided_by,
    }
    if resolution.decision == "approved":
        data["persona"] = resolution.persona
        data["cli"] = resolution.cli
        data["prompt"] = resolution.prompt
        data["teammate_name"] = resolution.teammate_name
        data["requested_by"] = resolution.requested_by
    return data


def _resolution_from_dict(data: dict) -> SpawnResolution:
    return SpawnResolution(
        request_id=data["request_id"],
        decision=data["decision"],
        decided_at=data["decided_at"],
        decided_by=data["decided_by"],
        persona=data.get("persona"),
        cli=data.get("cli"),
        prompt=data.get("prompt"),
        teammate_name=data.get("teammate_name"),
        requested_by=data.get("requested_by"),
    )


def _parse_apr_number(request_id: str) -> int | None:
    match = _APR_ID_PATTERN.match(request_id)
    if not match:
        return None
    return int(match.group(1))


def _next_request_id(session_dir: Path) -> str:
    max_num = 0
    pending = _pending_path(session_dir)
    if pending.exists():
        data = read_json(pending)
        num = _parse_apr_number(data.get("request_id", ""))
        if num is not None:
            max_num = max(max_num, num)

    resolutions = _resolutions_path(session_dir)
    if resolutions.exists():
        for line in resolutions.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            num = _parse_apr_number(data.get("request_id", ""))
            if num is not None:
                max_num = max(max_num, num)

    return f"apr-{max_num + 1:03d}"


def _write_pending(session_dir: Path, request: SpawnRequest) -> None:
    write_json(_pending_path(session_dir), _request_to_dict(request))


def _clear_pending(session_dir: Path) -> None:
    path = _pending_path(session_dir)
    if path.exists():
        path.unlink()


def _append_resolution(session_dir: Path, resolution: SpawnResolution) -> None:
    path = _resolutions_path(session_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(_resolution_to_dict(resolution))
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _validate_request_fields(
    *,
    persona: str,
    cli: str,
    requested_by: str,
    teammate_name: str | None,
) -> None:
    safe_segment(persona, "persona")
    safe_segment(requested_by, "requester")
    if cli not in _VALID_CLI:
        raise ValueError(f"Invalid cli: {cli!r}")
    if teammate_name is not None:
        safe_segment(teammate_name, "teammate")


def _load_pending(session_dir: Path) -> SpawnRequest | None:
    path = _pending_path(session_dir)
    if not path.exists():
        return None
    request = _request_from_dict(read_json(path))
    _validate_request_fields(
        persona=request.persona,
        cli=request.cli,
        requested_by=request.requested_by,
        teammate_name=request.teammate_name,
    )
    return request


def _require_pending(session_dir: Path, request_id: str) -> SpawnRequest:
    pending = _load_pending(session_dir)
    if pending is None:
        raise SpawnRequestNotFoundError("No pending spawn request")
    if pending.request_id != request_id:
        raise SpawnRequestMismatchError(
            f"Request id mismatch: expected {pending.request_id!r}, got {request_id!r}"
        )
    return pending


class SpawnApproval:
    def request_spawn(
        self,
        session_dir: Path,
        *,
        persona: str,
        cli: str,
        prompt: str,
        requested_by: str,
        teammate_name: str | None = None,
        event_log: EventLog | None = None,
    ) -> SpawnRequest:
        if _pending_path(session_dir).exists():
            raise SpawnPendingError("A spawn request is already pending")

        _validate_request_fields(
            persona=persona,
            cli=cli,
            requested_by=requested_by,
            teammate_name=teammate_name,
        )

        now = format_ts(utc_now())
        request = SpawnRequest(
            request_id=_next_request_id(session_dir),
            persona=persona,
            cli=cli,
            prompt=prompt,
            prompt_preview=_make_preview(prompt),
            teammate_name=teammate_name,
            requested_by=requested_by,
            requested_at=now,
        )
        _write_pending(session_dir, request)

        if event_log is not None:
            event_log.append(
                session_dir,
                type_="spawn_requested",
                payload={
                    "request_id": request.request_id,
                    "persona": persona,
                    "cli": cli,
                    "requested_by": requested_by,
                },
            )
        return request

    def get_pending(self, session_dir: Path) -> SpawnRequest | None:
        return _load_pending(session_dir)

    def approve(
        self,
        session_dir: Path,
        request_id: str,
        *,
        decided_by: str = "user",
        event_log: EventLog | None = None,
    ) -> SpawnResolution:
        pending = _require_pending(session_dir, request_id)
        resolution = SpawnResolution(
            request_id=pending.request_id,
            decision="approved",
            decided_at=format_ts(utc_now()),
            decided_by=decided_by,
            persona=pending.persona,
            cli=pending.cli,
            prompt=pending.prompt,
            teammate_name=pending.teammate_name,
            requested_by=pending.requested_by,
        )
        _append_resolution(session_dir, resolution)
        if event_log is not None:
            event_log.append(
                session_dir,
                type_="spawn_approved",
                payload={"request_id": pending.request_id, "persona": pending.persona},
            )
        _clear_pending(session_dir)
        return resolution

    def deny(
        self,
        session_dir: Path,
        request_id: str,
        *,
        decided_by: str = "user",
        event_log: EventLog | None = None,
    ) -> SpawnResolution:
        pending = _require_pending(session_dir, request_id)
        resolution = SpawnResolution(
            request_id=pending.request_id,
            decision="denied",
            decided_at=format_ts(utc_now()),
            decided_by=decided_by,
        )
        _append_resolution(session_dir, resolution)
        if event_log is not None:
            event_log.append(
                session_dir,
                type_="spawn_denied",
                payload={"request_id": pending.request_id},
            )
        _clear_pending(session_dir)
        return resolution

    def read_resolutions(self, session_dir: Path) -> list[SpawnResolution]:
        path = _resolutions_path(session_dir)
        if not path.exists():
            return []
        resolutions: list[SpawnResolution] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                resolutions.append(_resolution_from_dict(data))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        return resolutions
