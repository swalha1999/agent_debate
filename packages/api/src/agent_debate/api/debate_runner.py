"""Injectable debate runner — the SDK seam for the routes (task 10.2, #69).

The ``POST /debates`` route must START a real debate via the SDK
(:class:`~agent_debate.core.DebateEngine`), but a full run is long-running and
makes model calls. So the *act of running* is factored behind a small callable
seam, :data:`DebateRunner`: ``(topic, overrides) -> DebateResult``. Production
uses :func:`default_runner` (drives the SDK; every model call routes through the
Epic-13 gatekeeper inside the engine). Tests inject a stub via
:func:`set_debate_runner` that returns a canned result instantly — no network,
no API key.

No hard-coded values: overrides are applied to the process
:class:`~agent_debate.core.Settings` (via :meth:`Settings.model_copy`), so the
engine's per-run budget still comes from config, not inline literals.
"""

from __future__ import annotations

from typing import Protocol

from agent_debate.core import (
    DebateConfig,
    DebateEngine,
    DebateResult,
    get_settings,
)
from fastapi import FastAPI

#: ``app.state`` attribute holding the active runner (single source of truth).
RUNNER_ATTR = "debate_runner"


class DebateRunner(Protocol):
    """A callable that runs a debate and returns its :class:`DebateResult`."""

    def __call__(self, topic: str, overrides: dict[str, object]) -> DebateResult:
        """Run a debate on ``topic`` applying config ``overrides``."""
        ...


def default_runner(topic: str, overrides: dict[str, object]) -> DebateResult:
    """Run a debate via the SDK, applying ``overrides`` to process settings.

    Builds a :class:`~agent_debate.core.DebateEngine` from the (possibly
    overridden) settings and runs it to completion. Real runs need an API key and
    route every model call through the Epic-13 gatekeeper inside the engine.
    """
    settings = get_settings()
    if overrides:
        settings = settings.model_copy(update=overrides)
    engine = DebateEngine(DebateConfig.from_settings(settings), settings=settings)
    return engine.run(topic)


def set_debate_runner(app: FastAPI, runner: DebateRunner) -> None:
    """Install ``runner`` on ``app.state`` (tests substitute a stub here)."""
    setattr(app.state, RUNNER_ATTR, runner)


def get_debate_runner(app: FastAPI) -> DebateRunner:
    """Return the runner installed on ``app.state`` (defaults if unset)."""
    runner: DebateRunner = getattr(app.state, RUNNER_ATTR, default_runner)
    return runner


__all__ = [
    "DebateRunner",
    "RUNNER_ATTR",
    "default_runner",
    "get_debate_runner",
    "set_debate_runner",
]
