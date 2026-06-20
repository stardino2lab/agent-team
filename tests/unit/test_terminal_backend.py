"""TerminalBackend abstraction: factory, quoting, Protocol, exception aliases (S13a)."""

from __future__ import annotations

import shlex
import sys

import pytest

from agent_team.psmux_backend import (
    PsmuxBackend,
    PsmuxCommandError,
    PsmuxNotFoundError,
)
from agent_team.terminal_backend import (
    BackendCommandError,
    BackendNotFoundError,
    TerminalBackend,
    make_terminal_backend,
    quote_pane_arg,
)

_REAL_WHICH = "agent_team.psmux_backend.shutil.which"


# --- quote_pane_arg ---------------------------------------------------------


def test_quote_pane_arg_windows_double_quote_wraps_keeping_backslashes() -> None:
    # Windows pane shell: double-quote wrap, separators UNCHANGED (no .as_posix()).
    assert quote_pane_arg(r"C:\Users\a b\x.json", shell_family="windows") == (
        r'"C:\Users\a b\x.json"'
    )


def test_quote_pane_arg_posix_uses_shlex() -> None:
    value = "/home/a b/x.json"
    assert quote_pane_arg(value, shell_family="posix") == shlex.quote(value)


def test_quote_pane_arg_rejects_unknown_shell_family() -> None:
    with pytest.raises(ValueError):
        quote_pane_arg("x", shell_family="fish")  # type: ignore[arg-type]


# --- factory ----------------------------------------------------------------


def test_factory_mock_short_circuits_before_which_on_any_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The unit/CI path: mock=True must work with NO terminal binary, any platform,
    # even with AGENT_TEAM_BACKEND pointing elsewhere. Must NOT call which / raise.
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("AGENT_TEAM_BACKEND", "tmux")
    monkeypatch.setattr(_REAL_WHICH, lambda _name: None)
    backend = make_terminal_backend(mock=True)
    assert isinstance(backend, PsmuxBackend)
    assert backend.name == "psmux"


def test_factory_win32_default_is_psmux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("AGENT_TEAM_BACKEND", raising=False)
    monkeypatch.setattr(_REAL_WHICH, lambda _name: "C:\\psmux.exe")
    backend = make_terminal_backend()
    assert backend.name == "psmux"


def test_factory_env_psmux_overrides_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("AGENT_TEAM_BACKEND", "psmux")
    monkeypatch.setattr(_REAL_WHICH, lambda _name: "/usr/bin/psmux")
    assert make_terminal_backend().name == "psmux"


def test_factory_env_tmux_builds_tmux_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_TEAM_BACKEND", "tmux")
    monkeypatch.setattr(_REAL_WHICH, lambda _name: "/usr/bin/tmux")
    backend = make_terminal_backend()
    assert backend.name == "tmux"


def test_factory_non_win32_default_selects_tmux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("AGENT_TEAM_BACKEND", raising=False)
    monkeypatch.setattr(_REAL_WHICH, lambda _name: "/usr/bin/tmux")
    assert make_terminal_backend().name == "tmux"


def test_factory_missing_tmux_raises_backend_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_TEAM_BACKEND", "tmux")
    monkeypatch.setattr(_REAL_WHICH, lambda _name: None)
    with pytest.raises(BackendNotFoundError):
        make_terminal_backend()


def test_factory_invalid_env_value_is_explicit_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_TEAM_BACKEND", "screen")
    with pytest.raises(ValueError):
        make_terminal_backend()


def test_factory_missing_psmux_raises_backend_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("AGENT_TEAM_BACKEND", raising=False)
    monkeypatch.setattr(_REAL_WHICH, lambda _name: None)
    # The cli/start.py + cli/attach.py catch-sites catch PsmuxNotFoundError.
    with pytest.raises(PsmuxNotFoundError):
        make_terminal_backend()


# --- Protocol + name --------------------------------------------------------


def test_psmux_backend_satisfies_protocol() -> None:
    assert isinstance(PsmuxBackend(mock=True), TerminalBackend)


def test_psmux_backend_name() -> None:
    assert PsmuxBackend(mock=True).name == "psmux"


# --- exception aliases (back-compat) ----------------------------------------


def test_exception_aliases_are_identical_classes() -> None:
    # Existing `except PsmuxNotFoundError` / `except PsmuxCommandError` callers must
    # keep firing now that the canonical classes are the neutral ones.
    assert PsmuxNotFoundError is BackendNotFoundError
    assert PsmuxCommandError is BackendCommandError


def test_backend_not_found_is_file_not_found() -> None:
    assert issubclass(BackendNotFoundError, FileNotFoundError)


def test_backend_command_error_carries_attributes() -> None:
    err = BackendCommandError(
        "boom", exit_code=2, command_args=["new-session"], stderr="bad"
    )
    assert err.exit_code == 2
    assert err.stderr == "bad"
    assert err.command_args == ["new-session"]
    assert err.args == ["new-session"]  # .args alias preserved
