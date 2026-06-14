"""teammate-side CLI command tests."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from agent_team.__main__ import main
from agent_team.session import SessionStore


def test_teammate_ready_writes_marker(
    cli_env: dict[str, str],
    consumer_project: Path,
    session_store: SessionStore,
) -> None:
    sid = "rdy"
    session_store.create(
        session_id=sid, project_path=str(consumer_project), psmux_session=sid
    )
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["teammate", "ready", "--session", sid, "--as", "helper-1"],
        env=cli_env,
    )
    assert result.exit_code == 0, result.output

    marker = session_store.session_dir(sid) / "teammates" / "helper-1" / "ready"
    assert marker.exists()
    data = json.loads(marker.read_text(encoding="utf-8"))
    assert data["name"] == "helper-1"
    assert "ts" in data


def test_teammate_ready_is_idempotent(
    cli_env: dict[str, str],
    consumer_project: Path,
    session_store: SessionStore,
) -> None:
    sid = "rdy-idem"
    session_store.create(
        session_id=sid, project_path=str(consumer_project), psmux_session=sid
    )
    runner = CliRunner()
    args = ["teammate", "ready", "--session", sid, "--as", "helper-1"]
    assert runner.invoke(main, args, env=cli_env).exit_code == 0
    assert runner.invoke(main, args, env=cli_env).exit_code == 0
    marker = session_store.session_dir(sid) / "teammates" / "helper-1" / "ready"
    assert marker.exists()


def test_teammate_ready_rejects_unsafe_name(
    cli_env: dict[str, str],
    consumer_project: Path,
    session_store: SessionStore,
) -> None:
    sid = "rdy-bad"
    session_store.create(
        session_id=sid, project_path=str(consumer_project), psmux_session=sid
    )
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["teammate", "ready", "--session", sid, "--as", "../evil"],
        env=cli_env,
    )
    assert result.exit_code != 0
    assert not (session_store.session_dir(sid) / "teammates").exists()
