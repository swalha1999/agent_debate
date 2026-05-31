"""Synchronous start-of-request preflight seam (task 10.4, issue #71).

``POST /debates`` schedules the actual run on a background worker that *swallows*
exceptions (it must never crash). That is right for faults *during* a run, but a
misconfiguration we can detect *before* starting — most importantly a missing
provider API key (:class:`~agent_debate.core.validation.MissingApiKeyError`,
task 2.3) — should fail the request *synchronously* so the client gets a clear,
safe error instead of a silently ``failed`` run.

So the route calls a small ``() -> None`` preflight before scheduling the worker.
Production uses :func:`default_preflight`, which validates the active providers'
keys against the process settings. Tests inject a stub via :func:`set_preflight`
that raises (or no-ops), with no network and no real key.
"""

from __future__ import annotations

from typing import Protocol

from agent_debate.api.debate_runner import RUNNER_ATTR
from agent_debate.api.stream_runner import STREAM_RUNNER_ATTR
from agent_debate.core import get_settings
from agent_debate.core.validation import validate_required_keys
from fastapi import FastAPI

#: ``app.state`` attribute holding the active preflight (single source of truth).
PREFLIGHT_ATTR = "debate_preflight"


class Preflight(Protocol):
    """A no-arg check run before a debate starts; raises to reject the request."""

    def __call__(self) -> None:
        """Validate start-up preconditions; raise a typed error to reject."""
        ...


def _noop_preflight() -> None:
    """No-op preflight — used when an injected runner owns its preconditions."""


def default_preflight() -> None:
    """Validate that every active provider's required API key is present.

    Delegates to :func:`~agent_debate.core.validation.validate_required_keys`
    against the process :class:`~agent_debate.core.Settings`, so a missing key
    surfaces as a clear :class:`MissingApiKeyError` *before* a doomed run starts
    (the error handler maps it to a safe 503 that never echoes the key value).
    """
    validate_required_keys(get_settings())


def set_preflight(app: FastAPI, preflight: Preflight) -> None:
    """Install ``preflight`` on ``app.state`` (tests substitute a stub here)."""
    setattr(app.state, PREFLIGHT_ATTR, preflight)


def get_preflight(app: FastAPI) -> Preflight:
    """Return the preflight to run before a debate starts (resolution order).

    An explicit preflight installed via :func:`set_preflight` always wins. Else,
    if a custom runner / streaming runner was injected (a test or embedder stub
    that owns its own preconditions and makes no real provider call), the
    preflight is a no-op. Otherwise the production :func:`default_preflight`
    validates that the active providers' API keys are present.
    """
    explicit = getattr(app.state, PREFLIGHT_ATTR, None)
    if explicit is not None:
        return explicit  # type: ignore[no-any-return]
    has_injected_runner = getattr(app.state, STREAM_RUNNER_ATTR, None) is not None or (
        getattr(app.state, RUNNER_ATTR, None) is not None
    )
    return _noop_preflight if has_injected_runner else default_preflight


__all__ = [
    "PREFLIGHT_ATTR",
    "Preflight",
    "default_preflight",
    "get_preflight",
    "set_preflight",
]
