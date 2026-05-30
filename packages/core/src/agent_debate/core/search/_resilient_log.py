"""Structured log emitters for the resilient search wrapper (task 3.4).

``docs/prds/search-plugin.md`` §6: every scheduled retry of a flaky search and
every *persistent* failure that degrades to an empty result must be logged via
the LOG package, so a debate's graceful search degradation is observable in the
run log. This module owns just those two emit helpers so
:class:`~agent_debate.core.search.resilient.ResilientSearchProvider` stays focused
on policy; it binds ``run_id`` + ``runs_dir`` once.

The only literals here are logging *identifiers* (the ``agent`` label and the
``event_type`` kinds) — names, never config values. A persistent failure maps to
the LOG schema's dedicated ``timeout`` kind (the canonical "search gave up"
signal); each scheduled retry maps to the ``retry`` kind (PRD §5.8).
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.log import log_event

#: ``agent`` label stamped on resilient-search log events (a name, not a value).
_LOG_AGENT = "search"

#: ``event_type`` for each scheduled retry of a transient search failure (§6).
_LOG_RETRY_EVENT_TYPE = "retry"

#: ``event_type`` for a persistent failure/timeout that degrades to ``[]`` (§6).
_LOG_FAILURE_EVENT_TYPE = "timeout"


class _ResilientLog:
    """Emits the wrapper's retry + persistent-failure events for one run.

    Binds ``run_id`` and ``runs_dir`` once so callers pass only event-specific
    fields, keeping the LOG schema mapping in a single place.
    """

    def __init__(self, run_id: str, runs_dir: Path | str) -> None:
        self._run_id = run_id
        self._runs_dir = runs_dir

    def retry(self, backend: str, retry: int, delay: float, exc: BaseException) -> None:
        """Emit one ``retry`` event for a scheduled retry of a transient failure.

        Records the 1-based ``retry`` number, the backoff ``delay`` seconds and the
        error type so repeated transient search failures are observable (§6).
        """
        log_event(
            run_id=self._run_id,
            agent=_LOG_AGENT,
            event_type=_LOG_RETRY_EVENT_TYPE,
            round=0,
            payload={
                "backend": backend,
                "retry": retry,
                "delay_seconds": delay,
                "error": type(exc).__name__,
            },
            runs_dir=self._runs_dir,
        )

    def degraded(self, backend: str, query: str, exc: BaseException) -> None:
        """Emit one ``timeout`` event when a search gives up and returns ``[]``.

        Records the offending ``backend``, ``query`` and the final error type, so
        the graceful degradation (empty result, never a crash) is logged (§6).
        """
        log_event(
            run_id=self._run_id,
            agent=_LOG_AGENT,
            event_type=_LOG_FAILURE_EVENT_TYPE,
            round=0,
            payload={
                "backend": backend,
                "query": query,
                "error": type(exc).__name__,
            },
            runs_dir=self._runs_dir,
        )


__all__ = ["_ResilientLog"]
