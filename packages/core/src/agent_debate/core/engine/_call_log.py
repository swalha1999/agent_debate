"""Structured log emitters for the per-turn timeout/retry wrapper (issue #49).

Orchestration sub-PRD §4: every per-turn model call that exceeds ``turn_timeout_s``
(a ``timeout`` event), every scheduled retry of one (a ``retry`` event) and the
final abandonment after the budget is exhausted (a ``system`` event informing the
controller) must be logged via the LOG package, so a turn's resilience is
observable in the run log. This module owns just those three emit helpers so
:mod:`agent_debate.core.engine._call` stays focused on policy; it binds ``run_id``,
``round`` and ``runs_dir`` once.

The only literals here are LOG schema *identifiers* (event-type kinds + the
``turn_failed`` tag), names rather than config values — the kinds come from
:mod:`agent_debate.core.constants`.
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.core import constants
from agent_debate.log import log_event


class _CallLog:
    """Emits a turn's timeout / retry / turn-failed events for one round.

    Binds ``run_id``, ``agent``, ``round`` and ``runs_dir`` once so callers pass
    only event-specific fields, keeping the LOG schema mapping in a single place.
    """

    def __init__(self, *, run_id: str, agent: str, round_: int, runs_dir: Path | str) -> None:
        self._run_id = run_id
        self._agent = agent
        self._round = round_
        self._runs_dir = runs_dir

    def timeout(self, timeout_s: float, exc: BaseException) -> None:
        """Emit one ``timeout`` event for a model call that exceeded the budget."""
        self._emit(
            constants.TURN_TIMEOUT_EVENT_TYPE,
            {"timeout_seconds": timeout_s, "error": type(exc).__name__},
        )

    def retry(self, retry: int, delay: float, exc: BaseException) -> None:
        """Emit one ``retry`` event for a scheduled retry of a transient failure.

        Records the 1-based ``retry`` number, the backoff ``delay`` seconds and the
        error type so repeated transient turn failures are observable (§4).
        """
        self._emit(
            constants.TURN_RETRY_EVENT_TYPE,
            {"retry": retry, "delay_seconds": delay, "error": type(exc).__name__},
        )

    def failed(self, exc: BaseException) -> None:
        """Emit one ``system`` event informing the controller the turn was abandoned.

        Records the ``turn_failed`` tag + the final error type so the loop/controller
        can mark the turn FAILED and continue gracefully, never crashing (§4).
        """
        self._emit(
            constants.TURN_FAILED_EVENT_TYPE,
            {"turn_failed": constants.TURN_FAILED_TAG, "error": type(exc).__name__},
        )

    def _emit(self, event_type: str, payload: dict[str, object]) -> None:
        log_event(
            run_id=self._run_id,
            agent=self._agent,
            event_type=event_type,
            round=self._round,
            payload=payload,
            runs_dir=self._runs_dir,
        )


__all__ = ["_CallLog"]
