"""Orchestrator: bridges spawn approvals to teammate panes."""

from __future__ import annotations

import json
import shutil
import sys
import threading
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from agent_team import recovery
from agent_team._io import parse_ts, utc_now
from agent_team._watcher import FileWatcher
from agent_team.cli_registry import (
    LeadCliNotSupportedError,
    get_cli_spec,
    is_lead_supported,
)
from agent_team.event_log import EventLog
from agent_team.project_loader import ProjectLoader
from agent_team.session import Member, Session, SessionStore, default_base_dir
from agent_team.spawn_approval import SpawnApproval, SpawnResolution
from agent_team.teammate_runner import TeammateRunner
from agent_team.terminal_backend import BackendCommandError, TerminalBackend

# Tail bound for reconcile_handled's events.jsonl ingest on attach (D9). Generous
# on purpose: correctness rests on session.json, not the log. The handled-signals
# `member.request_id` and `teammate_name` are read from the COMPLETE session, so a
# teammate_ready/error event aging past this many entries can at worst cause one
# redundant `error` re-log on attach — never a double-spawn (a spawned teammate
# persists as a member). 2000 events ≫ any realistic single session.
_RECONCILE_EVENT_TAIL = 2000


# Bootstrap prompt for a codex lead (codex exec's PROMPT arg). One line, no double
# quotes (it is wrapped in "..." on the launch command line). The full lead
# context (D6 preamble + TEAM.md + playbook) is delivered via the working-root
# AGENTS.md, since codex has no --append-system-prompt-file.
_CODEX_LEAD_BOOTSTRAP = (
    "Read AGENTS.md in this working directory and orchestrate the team strictly "
    "per it, using ONLY the agent-team MCP tools. Do not read, edit, or run "
    "project code yourself."
)


def _lead_mcp_server_config(session_id: str, project_path: Path) -> dict:
    """The agent-team MCP server entry shared by every lead-config format.

    Runs under sys.executable (the interpreter with agent_team installed), not a
    bare 'python' that may differ in the pane. AGENT_TEAM_HOME captured at write
    time from default_base_dir().
    """
    return {
        "command": sys.executable,
        "args": ["-m", "agent_team.mcp_server"],
        "env": {
            "AGENT_TEAM_HOME": str(default_base_dir()),
            "AGENT_TEAM_SESSION_ID": session_id,
            "AGENT_TEAM_PROJECT_PATH": str(project_path.resolve()),
        },
    }


def _codex_mcp_c_flags(server_cfg: dict) -> list[str]:
    """Inline `-c` overrides that define [mcp_servers.agent-team] for codex exec.

    codex does NOT load [mcp_servers.*] from a `--profile` overlay file (verified
    live, s11c, against codex 0.141): MCP servers are read only from the base
    config or from `-c` inline overrides. So the lead's agent-team server is
    injected on the launch line via `-c`, which composes with --ignore-user-config
    — the base config is skipped, so the lead sees ONLY this server, none of the
    user's own MCP servers (the isolation the dead profile approach aimed for).

    Encoding (each `-c` value is parsed by codex as TOML): every value is a TOML
    LITERAL string (single-quoted). Literal strings take backslashes verbatim, so
    Windows paths need no escaping, and their single-quote delimiters never collide
    with the shell DOUBLE-quote wrap applied to the whole `key=value` token in the
    launch line. Returns a flat ["-c", '"<frag>"', "-c", '"<frag>"', ...] list.

    Quoting constraints on the values:
    - A single quote `'` can't live in a TOML literal string AND would also break
      the shell-token boundary, so it is rejected loudly below (its realistic
      source is a Windows username with an apostrophe, e.g. C:\\Users\\O'Brien,
      which would otherwise hand codex a malformed command and silently reproduce
      the "lead has no agent-team tools" failure). Full apostrophe support is a
      separate follow-up.
    - `$` and backtick are SAFE here on Windows (PowerShell does not expand inside
      double quotes) but would be expanded by a POSIX pane shell (bash/tmux). Our
      values (python exe, agent-team home, session id, project path) don't contain
      them; the principled fix — routing every launch-line value through
      `quote_pane_arg(value, shell_family=...)` — is the planned module-wide rewire
      (it must also cover the claude arm), so it is deliberately NOT done piecemeal
      here.
    """

    def literal(value: str) -> str:
        if "'" in value:
            raise ValueError(
                f"codex -c MCP value contains a single quote, which cannot be "
                f"TOML-literal-encoded for the launch line: {value!r}. "
                f"(A Windows username with an apostrophe is the usual cause — "
                f"use the claude lead, or move AGENT_TEAM_HOME off that path.)"
            )
        return f"'{value}'"

    prefix = "mcp_servers.agent-team"
    args_array = "[" + ",".join(literal(a) for a in server_cfg["args"]) + "]"
    fragments = [
        f"{prefix}.command={literal(server_cfg['command'])}",
        f"{prefix}.args={args_array}",
    ]
    fragments.extend(
        f"{prefix}.env.{key}={literal(value)}"
        for key, value in server_cfg["env"].items()
    )
    flags: list[str] = []
    for frag in fragments:
        flags.extend(["-c", f'"{frag}"'])
    return flags


def _write_codex_lead_agents_md(session_dir: Path, lead_context_text: str) -> Path:
    """Write the lead context to {session_dir}/lead/AGENTS.md; return the lead dir.

    codex exec -C <lead dir> uses this as its working root, so codex reads this
    AGENTS.md as the lead's system prompt (codex has no --append-system-prompt-file).
    Kept under session_dir (not the project) so the project's own AGENTS.md is not
    used and the project is not polluted.
    """
    lead_dir = session_dir / "lead"
    lead_dir.mkdir(parents=True, exist_ok=True)
    (lead_dir / "AGENTS.md").write_text(lead_context_text, encoding="utf-8")
    return lead_dir


def _check_lead_cli_supported(cli: str) -> None:
    """Raise early if config asks for a lead CLI the registry cannot launch.

    Kept at start() entry so an unsupported value never gets as far as
    creating a session_dir / psmux session — the user just sees a clean
    LeadCliNotSupportedError pointing at S12+.
    """
    if not is_lead_supported(cli):
        raise LeadCliNotSupportedError(
            f"Lead CLI {cli!r} not supported yet "
            f"(agy/Antigravity lead planned for S12+)"
        )


def _write_lead_mcp_config(
    session_dir: Path, session_id: str, project_path: Path, *, cli: str
) -> Path:
    """Write the lead's MCP config file (json format only); return the written path.

    claude (json): {session_dir}/<registry filename>, loaded via --mcp-config.
    codex does NOT write a file — its MCP server rides the launch line as inline
    `-c` overrides (see _codex_mcp_c_flags), so the user's ~/.codex is never
    mutated. Calling this for a non-json format is therefore a programming error.
    """
    spec = get_cli_spec(cli)
    if spec.mcp_format == "json":
        server_cfg = _lead_mcp_server_config(session_id, project_path)
        filename = spec.mcp_config_filename
        assert filename is not None  # json format guarantees a filename (CliSpec)
        config = {"mcpServers": {"agent-team": server_cfg}}
        path = session_dir / filename
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return path
    raise LeadCliNotSupportedError(
        f"Lead CLI {cli!r} ({spec.mcp_format!r}) has no MCP config FILE to write; "
        "non-json leads deliver MCP on the launch line"
    )


def _write_lead_system_prompt(session_dir: Path, lead_context_text: str) -> Path:
    """Write the lead system prompt to {session_dir}/lead-system-prompt.md.

    File-based delivery is the only safe channel: the prompt is multi-line
    markdown that may contain shell-meta characters (`$`, backticks, quotes,
    raw newlines). Passing it through psmux send_keys + cmd.exe / PowerShell
    quoting on Windows mangles or breaks the launch line. Claude reads the
    file directly via --append-system-prompt-file so no shell interpretation
    happens.
    """
    path = session_dir / "lead-system-prompt.md"
    path.write_text(lead_context_text, encoding="utf-8")
    return path


def _build_lead_launch_command(
    cli: str,
    *,
    mcp_config: Path | None = None,
    system_prompt_file: Path | None = None,
    session_id: str | None = None,
    project_path: Path | None = None,
    lead_dir: Path | None = None,
    output_last_message: Path | None = None,
) -> str:
    """Compose the lead CLI launch line send_keys'd to the lead pane (per-CLI).

    claude: --mcp-config <json> --strict-mcp-config --append-system-prompt-file.
    codex: codex exec --ignore-user-config --skip-git-repo-check <inline -c MCP
    overrides> -C <lead dir> -o ... + a bootstrap PROMPT (the lead context rides
    the working-root AGENTS.md, since codex has no --append-system-prompt-file).
    The agent-team MCP server is injected via `-c` (NOT a --profile overlay: codex
    does not load [mcp_servers.*] from a profile — verified live, s11c). Stays an
    elif chain (no Protocol), per the S9 decision. Only registered lead CLIs reach
    here (start() gates via _check_lead_cli_supported).
    """
    if cli == "claude":
        # Full resolved exe (Windows: claude.CMD shim resolution is inconsistent
        # across PowerShell profiles); falls back to the bare name off PATH.
        exe = shutil.which(cli) or cli
        return (
            f'{exe} --mcp-config "{mcp_config}" --strict-mcp-config '
            f'--append-system-prompt-file "{system_prompt_file}"'
        )
    if cli == "codex":
        exe = shutil.which(cli) or cli
        assert session_id is not None and project_path is not None
        mcp_flags = _codex_mcp_c_flags(
            _lead_mcp_server_config(session_id, project_path)
        )
        return " ".join(
            [
                exe,
                "exec",
                "--ignore-user-config",
                "--skip-git-repo-check",
                *mcp_flags,
                "-C",
                f'"{lead_dir}"',
                "-o",
                f'"{output_last_message}"',
                f'"{_CODEX_LEAD_BOOTSTRAP}"',
            ]
        )
    # Defensive: a registered lead CLI without an arm is a registry/builder
    # mismatch. agy/Antigravity lands here until S12 adds its lead arm.
    raise LeadCliNotSupportedError(
        f"Lead CLI {cli!r} is registered but has no launch builder "
        f"(agy/Antigravity lead planned for S12+)"
    )


@dataclass
class OrchestratorContext:
    session_id: str
    session_dir: Path
    store: SessionStore
    approval: SpawnApproval
    runner: TeammateRunner
    psmux: TerminalBackend
    event_log: EventLog
    no_psmux: bool = False


class Orchestrator:
    """Drains the approval queue and spawns teammates idempotently."""

    def __init__(self, ctx: OrchestratorContext) -> None:
        self.ctx = ctx
        self._handled_request_ids: set[str] = set()
        self._watcher: FileWatcher | None = None
        self._ready_watcher: FileWatcher | None = None
        # S14b: a single short-lived timer, armed ONLY while a retry is
        # outstanding, drives the backoff re-attempt (the FileWatchers are
        # edge-triggered, so a failed spawn would otherwise never wake again).
        self._retry_timer: threading.Timer | None = None
        # Serializes member mutations across the approval watcher thread
        # (run_once) and the teammates watcher thread (poll_ready). Reentrant so
        # run_once can call poll_ready while holding it.
        self._lock = threading.RLock()

    def start_watching(self) -> None:
        """Watch approval/ (run_once) and teammates/ (poll_ready) for changes.

        Each watcher is guarded independently so a partial-start (one created,
        the other not) is repaired on the next call rather than leaving the
        ready watcher permanently off.
        """
        if self._watcher is None:
            approval_dir = self.ctx.session_dir / "approval"
            approval_dir.mkdir(parents=True, exist_ok=True)
            self._watcher = FileWatcher(
                approval_dir,
                self.run_once,
                label="ResolutionWatcher",
            )
            self._watcher.start()

        if self._ready_watcher is None:
            teammates_dir = self.ctx.session_dir / "teammates"
            teammates_dir.mkdir(parents=True, exist_ok=True)
            self._ready_watcher = FileWatcher(
                teammates_dir,
                self.poll_ready,
                recursive=True,
                label="ReadyWatcher",
            )
            self._ready_watcher.start()

    def stop_watching(self) -> None:
        if self._retry_timer is not None:
            self._retry_timer.cancel()
            self._retry_timer = None
        if self._watcher is not None:
            self._watcher.stop()
            self._watcher = None
        if self._ready_watcher is not None:
            self._ready_watcher.stop()
            self._ready_watcher = None

    def start(
        self,
        *,
        project_path: Path,
        playbook: str | None = None,
        context_text: str | None = None,
    ) -> Session:
        loader = ProjectLoader(project_path)
        config = loader.load_config()
        max_teammates = int(config.get("max_teammates", 5))
        playbook_mode = str(config.get("playbook_mode", "guide"))
        lead_cli = str(config.get("lead_cli", "claude"))
        _check_lead_cli_supported(lead_cli)

        psmux_session = self.ctx.session_id
        lead = Member(
            name="lead",
            role="lead",
            persona=None,
            cli=lead_cli,
            pane_id=None,
            backend=self.ctx.psmux.name,
            status="pending",
        )
        session = self.ctx.store.create(
            session_id=self.ctx.session_id,
            project_path=str(project_path),
            psmux_session=psmux_session,
            playbook=playbook,
            playbook_mode=playbook_mode,
            members=[lead],
            max_teammates=max_teammates,
        )

        try:
            members_started: list[str] = ["lead"]
            if not self.ctx.no_psmux:
                spec = get_cli_spec(lead_cli)
                lead_context = loader.build_lead_context(
                    playbook_name=playbook, extra_context=context_text
                )
                if spec.mcp_format == "json":
                    mcp_config_path = _write_lead_mcp_config(
                        self.ctx.session_dir,
                        self.ctx.session_id,
                        project_path,
                        cli=lead_cli,
                    )
                    prompt_path = _write_lead_system_prompt(
                        self.ctx.session_dir, lead_context.text
                    )
                    launch_cmd = _build_lead_launch_command(
                        lead_cli,
                        mcp_config=mcp_config_path,
                        system_prompt_file=prompt_path,
                    )
                else:  # codex: working-root AGENTS.md + inline -c MCP overrides
                    lead_dir = _write_codex_lead_agents_md(
                        self.ctx.session_dir, lead_context.text
                    )
                    launch_cmd = _build_lead_launch_command(
                        lead_cli,
                        session_id=self.ctx.session_id,
                        project_path=project_path,
                        lead_dir=lead_dir,
                        output_last_message=self.ctx.session_dir / "lead-last.txt",
                    )
                lead_pane = self.ctx.psmux.new_session(psmux_session, cwd=project_path)
                self.ctx.psmux.send_keys(lead_pane, launch_cmd)
                # CLI entry (not `python -m agent_team.tui`) so the session id
                # flows through argv. The module entry needs AGENT_TEAM_SESSION_ID,
                # which psmux.split_pane has no way to inject.
                self.ctx.psmux.split_pane(
                    psmux_session,
                    command=f"agent-team tui --session {self.ctx.session_id}",
                    cwd=project_path,
                )
                lead.pane_id = lead_pane
                lead.status = "running"
                self.ctx.store.update_members(self.ctx.session_id, [lead])
                members_started.append("tui")

            self.ctx.event_log.append(
                self.ctx.session_dir,
                type_="session_started",
                payload={
                    "session_id": self.ctx.session_id,
                    "psmux_session": psmux_session,
                    "playbook": playbook,
                    "playbook_mode": playbook_mode,
                    "members": members_started,
                    "context": context_text,
                },
            )
            self.run_once()
            self.start_watching()
        except Exception:
            # Partial start — tear down both sides of the split brain so the
            # next `start --session SAME` is not blocked by "already exists"
            # on disk or "duplicate session" on psmux.
            if not self.ctx.no_psmux:
                try:
                    self.ctx.psmux.kill_session(psmux_session)
                except Exception as psmux_exc:  # noqa: BLE001
                    print(
                        "Orchestrator.start psmux cleanup failed for "
                        f"{psmux_session!r}: {psmux_exc!r}",
                        file=sys.stderr,
                    )
            try:
                shutil.rmtree(self.ctx.session_dir)
            except OSError as cleanup_exc:
                print(
                    "Orchestrator.start cleanup failed for "
                    f"{self.ctx.session_dir}: {cleanup_exc!r}",
                    file=sys.stderr,
                )
            # No CODEX_HOME profile to clean up: the codex lead's MCP config rides
            # the launch line as inline `-c` overrides, writing nothing outside
            # session_dir (which the rmtree above already removes).
            raise
        return session

    def attach(self) -> Session:
        session = self.ctx.store.load(self.ctx.session_id)
        self.reconcile_handled()
        self.run_once()
        # Re-arm retries recorded before a detach so a backed-off spawn resumes.
        self._arm_retry_timer()
        self.start_watching()
        return session

    def reconcile_handled(self) -> None:
        """At attach time, re-derive the handled set from disk state.

        A resolution is treated as handled if any of the following hold:
        - decision is "denied"
        - an emitted teammate_ready or error event carries its request_id
        - a session member records its request_id (spawned, even if still
          "starting" — the S10b handshake defers teammate_ready, so the member
          is the authoritative "already spawned" signal)
        - its teammate_name already appears in session.members
        The member request_id channel is the strongest signal, because
        teammate_name is often None when the request did not pre-assign one and
        teammate_ready may not have fired yet.
        """
        ready_request_ids: set[str] = set()
        for event in self.ctx.event_log.read(
            self.ctx.session_dir, limit=_RECONCILE_EVENT_TAIL
        ):
            if event.type in ("teammate_ready", "error"):
                req_id = event.payload.get("request_id")
                if isinstance(req_id, str):
                    ready_request_ids.add(req_id)

        session = self.ctx.store.load(self.ctx.session_id)
        teammate_names = {m.name for m in session.members if m.role == "teammate"}
        member_request_ids = {
            m.request_id for m in session.members if m.request_id is not None
        }

        # Mutating the shared handled set under the lock keeps it consistent with
        # run_once (the approval watcher thread), which reads+writes it too.
        with self._lock:
            for res in self.ctx.approval.read_resolutions(self.ctx.session_dir):
                if res.decision == "denied":
                    self._handled_request_ids.add(res.request_id)
                elif res.request_id in ready_request_ids:
                    self._handled_request_ids.add(res.request_id)
                elif res.request_id in member_request_ids:
                    self._handled_request_ids.add(res.request_id)
                elif res.teammate_name and res.teammate_name in teammate_names:
                    self._handled_request_ids.add(res.request_id)

    def run_once(self) -> int:
        with self._lock:
            spawned = 0
            for res in self.ctx.approval.read_resolutions(self.ctx.session_dir):
                if res.request_id in self._handled_request_ids:
                    continue
                if res.decision != "approved":
                    self._handled_request_ids.add(res.request_id)
                    continue
                if self._spawn_one(res):
                    spawned += 1
                self._handled_request_ids.add(res.request_id)
            # Reconcile any ready markers written while detached / between ticks.
            self.poll_ready()
            return spawned

    def _spawn_one(self, res: SpawnResolution) -> bool:
        if res.persona is None or res.cli is None:
            self.ctx.event_log.append(
                self.ctx.session_dir,
                type_="error",
                payload={
                    "kind": "invalid_resolution",
                    "request_id": res.request_id,
                    "missing": [
                        f for f in ("persona", "cli") if getattr(res, f) is None
                    ],
                },
            )
            recovery.clear_retry(self.ctx.session_dir, res.request_id)
            return False
        session = self.ctx.store.load(self.ctx.session_id)
        existing_teammates = [m.name for m in session.members if m.role == "teammate"]
        teammate_count = len(existing_teammates)
        if teammate_count >= session.max_teammates:
            self.ctx.event_log.append(
                self.ctx.session_dir,
                type_="error",
                payload={
                    "kind": "max_teammates_exceeded",
                    "request_id": res.request_id,
                    "max_teammates": session.max_teammates,
                    "current": teammate_count,
                    "existing_teammates": existing_teammates,
                },
            )
            recovery.clear_retry(self.ctx.session_dir, res.request_id)
            return False
        teammate_name = res.teammate_name or self._next_teammate_name(session)
        persona = res.persona
        cli = res.cli

        if self.ctx.no_psmux:
            pane_id: str | None = None
        else:
            try:
                result = self.ctx.runner.spawn(
                    psmux_session=session.psmux_session,
                    persona=persona,
                    prompt=res.prompt or "",
                    teammate_name=teammate_name,
                    session_id=session.session_id,
                    session_dir=self.ctx.session_dir,
                    project_path=Path(session.project_path),
                )
            except BackendCommandError as exc:
                # Execution failure of an already-APPROVED spawn (transient pane/
                # CLI launch error) — retry the approved resolution without
                # re-approval, bounded + backed off. Hard stops above never reach here.
                return self._handle_spawn_failure(res, exc)
            pane_id = result.pane_id

        # status="starting": the teammate is not ready until it writes its ready
        # marker (S10b). poll_ready flips it to "running" and emits teammate_ready.
        members = list(session.members) + [
            Member(
                name=teammate_name,
                role="teammate",
                persona=res.persona,
                cli=cli,
                pane_id=pane_id,
                backend=self.ctx.psmux.name,
                status="starting",
                request_id=res.request_id,
            )
        ]
        self.ctx.store.update_members(session.session_id, members)
        recovery.clear_retry(self.ctx.session_dir, res.request_id)
        return True

    def _handle_spawn_failure(self, res: SpawnResolution, exc: Exception) -> bool:
        """Record a bounded, backed-off retry for an approved spawn, or give up.

        Returns False (the spawn did not produce a member this attempt). On
        exhaustion emits a terminal `error` event; otherwise records a retry and
        arms the timer. run_once still marks the request handled, but the timer's
        _retry_sweep re-attempts via _spawn_one directly, independent of that gate.
        """
        attempts = recovery.attempts_for(self.ctx.session_dir, res.request_id) + 1
        if attempts >= recovery.MAX_SPAWN_RETRIES:
            self.ctx.event_log.append(
                self.ctx.session_dir,
                type_="error",
                payload={
                    "kind": "spawn_failed",
                    "request_id": res.request_id,
                    "attempts": attempts,
                    "error": str(exc)[:500],
                },
            )
            recovery.clear_retry(self.ctx.session_dir, res.request_id)
            return False
        delay = recovery.backoff(attempts)
        recovery.record_retry(
            self.ctx.session_dir,
            request_id=res.request_id,
            attempts=attempts,
            next_eligible=utc_now() + timedelta(seconds=delay),
            last_error=str(exc),
        )
        self.ctx.event_log.append(
            self.ctx.session_dir,
            type_="spawn_retry_scheduled",
            payload={
                "request_id": res.request_id,
                "attempts": attempts,
                "delay_s": delay,
            },
        )
        self._arm_retry_timer()
        return False

    def _retry_sweep(self) -> None:
        """Re-attempt any retry whose backoff has elapsed (timer- or attach-driven)."""
        with self._lock:
            now = utc_now()
            retries = recovery.read_retries(self.ctx.session_dir)
            resolutions = {
                r.request_id: r
                for r in self.ctx.approval.read_resolutions(self.ctx.session_dir)
            }
            for rid, rec in retries.items():
                if parse_ts(rec.next_eligible_ts) <= now:
                    res = resolutions.get(rid)
                    if res is not None and res.decision == "approved":
                        self._spawn_one(res)
                    else:
                        # Eligible retry whose resolution is missing or no longer
                        # approved can never make progress. Drop it so the
                        # past-eligible record does not drive a 0-delay re-arm
                        # busy-loop.
                        recovery.clear_retry(self.ctx.session_dir, rid)
            self._arm_retry_timer()

    def _arm_retry_timer(self) -> None:
        """(Re)schedule the single retry timer for the soonest outstanding retry."""
        if self._retry_timer is not None:
            self._retry_timer.cancel()
            self._retry_timer = None
        retries = recovery.read_retries(self.ctx.session_dir)
        if not retries:
            return
        now = utc_now()
        soonest = min(parse_ts(r.next_eligible_ts) for r in retries.values())
        # Floor the delay so an already-past record (e.g. one re-attempted this
        # tick that records its next backoff only after this re-arm) cannot spin
        # the timer at 0s. _retry_sweep already clears un-actionable records.
        delay = max(0.5, (soonest - now).total_seconds())
        timer = threading.Timer(delay, self._retry_sweep)
        timer.daemon = True
        self._retry_timer = timer
        timer.start()

    def poll_ready(self) -> None:
        """Emit teammate_ready for any 'starting' teammate whose marker exists.

        Driven by the teammates-dir watcher and by run_once/attach so a marker
        written while detached is reconciled. Idempotent: a member already
        'running' is skipped, so a second watcher tick never re-emits.
        """
        with self._lock:
            session = self.ctx.store.load(self.ctx.session_id)
            updated = False
            for m in session.members:
                if m.role != "teammate" or m.status != "starting":
                    continue
                marker = self.ctx.session_dir / "teammates" / m.name / "ready"
                if not marker.exists():
                    continue
                m.status = "running"
                updated = True
                self.ctx.event_log.append(
                    self.ctx.session_dir,
                    type_="teammate_ready",
                    payload={
                        "request_id": m.request_id,
                        "persona": m.persona,
                        "name": m.name,
                        "pane_id": m.pane_id,
                        "cli": m.cli,
                    },
                )
            if updated:
                self.ctx.store.update_members(self.ctx.session_id, session.members)

    def _next_teammate_name(self, session: Session) -> str:
        existing = {m.name for m in session.members if m.role == "teammate"}
        i = 1
        while f"helper-{i}" in existing:
            i += 1
        return f"helper-{i}"
