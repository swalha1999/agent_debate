"""The ``ApiGatekeeper`` class — the chokepoint for external calls (task 13.2).

Sub-PRD ``docs/prds/api-gatekeeper.md`` §3: every external LLM/search call goes
through :meth:`ApiGatekeeper.execute`, which **checks rate limits before running
the call**, executes it, and **logs every call** (service, latency, outcome) via
the LOG package (``agent_debate.log``).

Scope (task 13.2): a straightforward *check → run → log* pipeline. The limit
check uses the in-process sliding-window :class:`._limiter._RateLimiter`; when a
window is exhausted it raises :class:`.errors.RateLimitExceededError` *before*
the callable runs. The FIFO overflow queue (13.3) and retry/concurrency refinements
(13.4) hook in at the marked seam in :meth:`execute`; :meth:`get_queue_status`
returns an empty :class:`.types.QueueStatus` until 13.5 fills it.

No limit values are hard-coded: thresholds come from the injected
:class:`RateLimitConfig`. The only literals are the logging ``agent`` label and
``event_type`` (identifiers, not limits).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from agent_debate.core.gatekeeper._limiter import _RateLimiter
from agent_debate.core.gatekeeper.config import DEFAULT_SERVICE, RateLimitConfig
from agent_debate.core.gatekeeper.errors import RateLimitExceededError
from agent_debate.core.gatekeeper.types import (
    OUTCOME_ERROR,
    OUTCOME_SUCCESS,
    CallOutcome,
    QueueStatus,
)
from agent_debate.log import DEFAULT_RUNS_DIR, log_event

_T = TypeVar("_T")

#: ``agent`` label stamped on gatekeeper log events (a name, not a limit value).
_LOG_AGENT = "gatekeeper"

#: ``event_type`` for an external API call routed through the gatekeeper. An
#: external call maps cleanly to the LOG schema's ``tool_call`` kind (PRD §5.8).
_LOG_EVENT_TYPE = "tool_call"

#: Milliseconds per second — a unit conversion for latency, not a magic number.
_MS_PER_SECOND = 1000.0


class ApiGatekeeper:
    """Centralized manager every external API call passes through (sub-PRD §3).

    Args:
        config: Parsed rate-limit config; per-service ceilings come from here.
        run_id: Debate run id used as logging context for every emitted event.
        runs_dir: Directory holding the per-run JSONL sink (LOG package).
    """

    def __init__(
        self,
        config: RateLimitConfig,
        *,
        run_id: str,
        runs_dir: Path | str = DEFAULT_RUNS_DIR,
    ) -> None:
        self._config = config
        self._run_id = run_id
        self._runs_dir = runs_dir
        self._limiter = _RateLimiter()

    def execute(
        self,
        api_call: Callable[..., _T],
        *args: Any,
        service: str = DEFAULT_SERVICE,
        **kwargs: Any,
    ) -> _T:
        """Check limits, run ``api_call(*args, **kwargs)``, and log the call.

        The rate limit for ``service`` (falling back to the ``default`` service)
        is checked *before* the callable runs; an exhausted window raises
        :class:`RateLimitExceededError` and the callable never executes. On success
        the result is returned; on failure the exception is re-raised. Either
        way one event is logged with ``service``, ``latency_ms`` and ``outcome``.

        Args:
            api_call: The external call to run (no real network in tests).
            *args: Positional arguments forwarded to ``api_call``.
            service: Service key selecting the rate limits (default ``"default"``).
            **kwargs: Keyword arguments forwarded to ``api_call``.

        Returns:
            Whatever ``api_call`` returns.
        """
        limits = self._config.get_service_limits(service)
        self._check_limits(service, limits)

        start = time.monotonic()
        try:
            result = api_call(*args, **kwargs)
        except BaseException:
            self._log_call(service, start, OUTCOME_ERROR)
            raise
        self._log_call(service, start, OUTCOME_SUCCESS)
        return result

    def get_queue_status(self) -> QueueStatus:
        """Return the overflow queue snapshot (empty until task 13.3/13.5)."""
        return QueueStatus()

    def _check_limits(self, service: str, limits: Any) -> None:
        """Admit the request or raise on an exhausted window.

        Seam for tasks 13.3/13.4: today an exhausted window raises
        :class:`RateLimitExceededError`; later the overflow queue/backpressure
        and concurrency control hook in here instead of raising.
        """
        exhausted = self._limiter.check(service, limits)
        if exhausted is not None:
            raise RateLimitExceededError(service, exhausted)
        self._limiter.record(service)

    def _log_call(self, service: str, start: float, outcome: CallOutcome) -> None:
        """Emit one structured event with service, latency_ms and outcome."""
        latency_ms = (time.monotonic() - start) * _MS_PER_SECOND
        log_event(
            run_id=self._run_id,
            agent=_LOG_AGENT,
            event_type=_LOG_EVENT_TYPE,
            round=0,
            payload={"service": service, "outcome": outcome},
            latency_ms=latency_ms,
            runs_dir=self._runs_dir,
        )


__all__ = ["ApiGatekeeper"]
