"""CLI logs command tests."""

from __future__ import annotations

import json

from click.testing import CliRunner

from agent_team import tasks as tasks_mod
from agent_team.__main__ import main
from agent_team.event_log import EventLog
from agent_team.session import Member, SessionStore


def test_logs_tail_and_export(cli_env: dict, session_store: SessionStore, tmp_path) -> None:
    session_store.create(
        session_id="cli-logs",
        project_path="c:\\DEV\\test",
        psmux_session="cli-logs",
    )
    runner = CliRunner()
    runner.invoke(
        main,
        ["mail", "send", "--session", "cli-logs", "--to", "lead", "--body", "ping"],
        env=cli_env,
    )

    tail = runner.invoke(
        main,
        ["logs", "tail", "--session", "cli-logs", "--lines", "5"],
        env=cli_env,
    )
    assert tail.exit_code == 0
    assert "mail_sent" in tail.output

    # Seed a teammate transcript so export bundles it alongside events.
    transcript = session_store.session_dir("cli-logs") / "teammates" / "helper-1" / "transcript.log"
    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_text("teammate did work\n", encoding="utf-8")

    dest = tmp_path / "bundle"
    export = runner.invoke(
        main,
        ["logs", "export", "--session", "cli-logs", "--to", str(dest)],
        env=cli_env,
    )
    assert export.exit_code == 0
    events_out = dest / "events.jsonl"
    assert events_out.exists()
    assert "mail_sent" in events_out.read_text(encoding="utf-8")
    transcript_out = dest / "transcripts" / "helper-1.log"
    assert transcript_out.exists()
    assert "teammate did work" in transcript_out.read_text(encoding="utf-8")


def test_logs_follow_once(cli_env: dict, session_store: SessionStore) -> None:
    session_store.create(
        session_id="cli-follow",
        project_path="c:\\DEV\\test",
        psmux_session="cli-follow",
    )
    runner = CliRunner()
    env = {**cli_env, "AGENT_TEAM_FOLLOW_ONCE": "1"}
    runner.invoke(
        main,
        ["mail", "send", "--session", "cli-follow", "--to", "lead", "--body", "x"],
        env=env,
    )
    follow = runner.invoke(
        main,
        ["logs", "tail", "--session", "cli-follow", "--follow"],
        env=env,
    )
    assert follow.exit_code == 0
    assert "mail_sent" in follow.output


# --- logs manifest (S16a) ---------------------------------------------------


def _seed_manifest_session(store: SessionStore) -> None:
    store.create(
        session_id="m1", project_path="c:\\proj", psmux_session="m1",
        members=[
            Member(name="lead", role="lead", persona=None, cli="claude",
                   pane_id="%0", backend="psmux", status="running"),
            Member(name="impl-1", role="teammate", persona="implementer", cli="codex",
                   pane_id="%1", backend="psmux", status="running",
                   request_id="apr-1"),
        ],
    )
    session_dir = store.session_dir("m1")
    log = EventLog()
    t = tasks_mod.create_task(session_dir, title="build", description="x", event_log=log)
    tasks_mod.claim_task(session_dir, t.id, assignee="impl-1", event_log=log)


def test_logs_manifest_json(cli_env: dict, session_store: SessionStore) -> None:
    _seed_manifest_session(session_store)
    result = CliRunner().invoke(
        main, ["logs", "manifest", "--session", "m1", "--format", "json"], env=cli_env
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["session_id"] == "m1"
    assert data["tasks"][0]["role"] == "implementer"


def test_logs_manifest_default_is_json(cli_env: dict, session_store: SessionStore) -> None:
    _seed_manifest_session(session_store)
    result = CliRunner().invoke(
        main, ["logs", "manifest", "--session", "m1"], env=cli_env
    )
    assert result.exit_code == 0, result.output
    json.loads(result.output)  # default renders parseable json


def test_logs_manifest_jsonl(cli_env: dict, session_store: SessionStore) -> None:
    _seed_manifest_session(session_store)
    result = CliRunner().invoke(
        main, ["logs", "manifest", "--session", "m1", "--format", "jsonl"], env=cli_env
    )
    assert result.exit_code == 0, result.output
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0])["session_id"] == "m1"


def test_logs_manifest_md(cli_env: dict, session_store: SessionStore) -> None:
    _seed_manifest_session(session_store)
    result = CliRunner().invoke(
        main, ["logs", "manifest", "--session", "m1", "--format", "md"], env=cli_env
    )
    assert result.exit_code == 0, result.output
    assert "# Session m1" in result.output
    assert "| task | status | role | assignee | title |" in result.output


def test_logs_manifest_unknown_session_exits_1(cli_env: dict) -> None:
    result = CliRunner().invoke(
        main, ["logs", "manifest", "--session", "nope", "--format", "json"], env=cli_env
    )
    assert result.exit_code == 1
