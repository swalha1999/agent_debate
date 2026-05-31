"""Tests for the config-driven Uvicorn entrypoint of the UI (task 11.1, #73).

We never bind a real port: :func:`uvicorn.run` is monkeypatched so we can assert
the host/port that ``run_server`` resolves from env / named-constant defaults.
"""

from __future__ import annotations

from typing import Any

import pytest
from agent_debate.ui import __main__ as entry
from agent_debate.ui.config import (
    DEFAULT_UI_HOST,
    DEFAULT_UI_PORT,
    resolve_host,
    resolve_port,
)


def test_defaults_come_from_named_constants(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no env override, host/port fall back to the named constants."""
    monkeypatch.delenv("UI_HOST", raising=False)
    monkeypatch.delenv("UI_PORT", raising=False)

    assert resolve_host() == DEFAULT_UI_HOST
    assert resolve_port() == DEFAULT_UI_PORT


def test_env_overrides_host_and_port(monkeypatch: pytest.MonkeyPatch) -> None:
    """``UI_HOST`` / ``UI_PORT`` env vars override the defaults."""
    monkeypatch.setenv("UI_HOST", "0.0.0.0")
    monkeypatch.setenv("UI_PORT", "4321")

    assert resolve_host() == "0.0.0.0"
    assert resolve_port() == 4321


def test_run_server_invokes_uvicorn_without_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``run_server`` calls ``uvicorn.run`` with the resolved host/port."""
    calls: dict[str, Any] = {}

    def fake_run(app: Any, *, host: str, port: int, **_: Any) -> None:
        calls["host"] = host
        calls["port"] = port

    monkeypatch.setenv("UI_HOST", "127.0.0.1")
    monkeypatch.setenv("UI_PORT", "4555")
    monkeypatch.setattr("uvicorn.run", fake_run)

    entry.run_server()

    assert calls == {"host": "127.0.0.1", "port": 4555}


def test_main_delegates_to_run_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """The console-script ``main`` delegates to :func:`run_server`."""
    called: list[bool] = []
    monkeypatch.setattr(entry, "run_server", lambda: called.append(True))

    entry.main()

    assert called == [True]
