"""The ``ApiGatekeeper`` class — the chokepoint for external calls (task 13.2).

Sub-PRD ``docs/prds/api-gatekeeper.md`` §3: every external LLM/search call goes
through :meth:`ApiGatekeeper.execute`, which **checks rate limits before running
the call**, executes it, and **logs every call** (service, latency, outcome) via
the LOG package (``agent_debate.log``).

Scope: a *check → run-or-enqueue → log* pipeline. The limit check uses the
in-process sliding-window :class:`._limiter._RateLimiter`; when a window is
exhausted the call is **enqueued** into a bounded per-service FIFO overflow queue
(:class:`._queue._OverflowQueue`, task 13.3) instead of being dropped or crashed.
A genuinely **full** queue raises :class:`.errors.QueueFullError` (backpressure).
:meth:`drain` runs queued calls in FIFO order as the rate windows reset (the
injectable clock makes "a window reset" deterministic in tests). Retry /
concurrency refinements (13.4) and the full :meth:`get_queue_status` (13.5) hook
in at the marked seams.

No limit values are hard-coded: thresholds come from the injected
:class:`RateLimitConfig`. The only literals are the logging ``agent`` label and
``event_type`` (identifiers, not limits).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from agent_debate.core.gatekeeper._events import _GatekeeperLog
from agent_debate.core.gatekeeper._limiter import _RateLimiter
from agent_debate.core.gatekeeper._queue import PendingCall, _OverflowQueue
from agent_debate.core.gatekeeper._retry import run_with_retry
from agent_debate.core.gatekeeper.config import DEFAULT_SERVICE, RateLimitConfig, ServiceLimits
from agent_debate.core.gatekeeper.errors import QueueFullError
from agent_debate.core.gatekeeper.types import OUTCOME_ERROR, OUTCOME_SUCCESS, QueueStatus
from agent_debate.log import DEFAULT_RUNS_DIR

_T = TypeVar("_T")


class ApiGatekeeper:
    """Centralized manager every external API call passes through (sub-PRD §3).

    Args:
        config: Parsed rate-limit config; per-service ceilings + queue depth come
            from here.
        run_id: Debate run id used as logging context for every emitted event.
        runs_dir: Directory holding the per-run JSONL sink (LOG package).
        time_fn: Monotonic clock for the sliding-window limiter; injectable so
            tests can advance a fake clock to reset windows and exercise drain.
        sleep_fn: Backoff sleep seam used between retries of a transient failure
            (task 13.4); injectable so tests capture delays without real waiting.
    """

    def __init__(
        self,
        config: RateLimitConfig,
        *,
        run_id: str,
        runs_dir: Path | str = DEFAULT_RUNS_DIR,
        time_fn: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config
        self._log = _GatekeeperLog(run_id, runs_dir)
        self._limiter = _RateLimiter(time_fn=time_fn)
        self._sleep_fn = sleep_fn
        # One bounded FIFO overflow queue per service (depth from that service's
        # config). Built lazily so unconfigured services inherit default depth.
        self._queues: dict[str, _OverflowQueue] = {}

    def execute(
        self,
        api_call: Callable[..., _T],
        *args: Any,
        service: str = DEFAULT_SERVICE,
        **kwargs: Any,
    ) -> _T | None:
        """Run ``api_call`` now if within limits, else enqueue it (FIFO).

        The rate limit for ``service`` (falling back to ``default``) is checked
        first. If a window is exhausted the call is **enqueued** into the bounded
        per-service overflow queue and ``None`` is returned (it runs later via
        :meth:`drain`) — overflow is never dropped or crashed (sub-PRD §5). Only
        a **full** queue raises :class:`QueueFullError` (backpressure). When the
        call runs (now or on drain) one event is logged with ``service``,
        ``latency_ms`` and ``outcome``.

        Args:
            api_call: The external call to run (no real network in tests).
            *args: Positional arguments forwarded to ``api_call``.
            service: Service key selecting the rate limits (default ``"default"``).
            **kwargs: Keyword arguments forwarded to ``api_call``.

        Returns:
            The callable's result when it ran immediately, else ``None`` (queued).
        """
        limits = self._config.get_service_limits(service)
        # Overflow when EITHER the rate window is exhausted OR the service is at
        # its concurrency cap: both back-pressure into the same FIFO queue rather
        # than dropping the call or exceeding ``concurrent_max`` (sub-PRD §4/§5).
        if self._limiter.check(service, limits) is not None or self._limiter.at_concurrency_cap(
            service, limits
        ):
            self._enqueue(service, limits, PendingCall(service, api_call, args, kwargs))
            return None
        self._limiter.record(service)
        return self._run(service, limits, api_call, args, kwargs)

    def drain(self) -> int:
        """Run queued calls now within their rate windows, in FIFO order.

        Walks each service's overflow queue oldest-first, running a pending call
        only while that service's window has room (re-checking after each, so a
        single window's freed capacity is honoured exactly). Returns the number
        of queued calls executed. Intended to be invoked as windows reset (e.g.
        after the injectable clock advances).
        """
        drained = 0
        for service, queue in self._queues.items():
            limits = self._config.get_service_limits(service)
            while queue.depth and self._limiter.check(service, limits) is None:
                pending = queue.dequeue()
                self._limiter.record(service)
                self._log.queue_event(service, "drain")
                self._run(service, limits, pending.api_call, pending.args, pending.kwargs)
                drained += 1
        return drained

    def get_queue_status(self, service: str = DEFAULT_SERVICE) -> QueueStatus:
        """Return the overflow queue snapshot for ``service`` (depth + stats).

        Reports real depth, the configured ``max_depth`` and lifetime
        enqueued/drained counters for the named service's FIFO queue (sub-PRD
        §3). Full multi-service reporting is task 13.5.
        """
        queue = self._queue_for(service)
        return QueueStatus(
            depth=queue.depth,
            max_depth=queue.max_depth,
            enqueued_total=queue.enqueued_total,
            drained_total=queue.drained_total,
        )

    def _enqueue(self, service: str, limits: ServiceLimits, pending: PendingCall) -> None:
        """Enqueue an overflowing call, or raise :class:`QueueFullError`."""
        queue = self._queue_for(service)
        if not queue.enqueue(pending):
            self._log.queue_event(service, "backpressure")
            raise QueueFullError(service, limits.queue_max_depth)
        self._log.queue_event(service, "enqueue")

    def _queue_for(self, service: str) -> _OverflowQueue:
        """Return (lazily creating) the bounded FIFO queue for ``service``."""
        queue = self._queues.get(service)
        if queue is None:
            limits = self._config.get_service_limits(service)
            queue = _OverflowQueue(limits.queue_max_depth)
            self._queues[service] = queue
        return queue

    def _run(
        self,
        service: str,
        limits: ServiceLimits,
        api_call: Callable[..., _T],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> _T:
        """Run ``api_call`` under the concurrency slot, retrying transient errors.

        The in-flight slot is held for the whole retry sequence (so a retrying
        call still counts against ``concurrent_max``) and always released. Each
        attempt logs service/latency/outcome; each scheduled retry logs a
        ``retry`` event with the backoff delay (sub-PRD §6/§7).
        """
        self._limiter.acquire(service)
        try:
            return run_with_retry(
                lambda: self._attempt(service, api_call, args, kwargs),
                max_retries=limits.max_retries,
                retry_after_seconds=limits.retry_after_seconds,
                sleep_fn=self._sleep_fn,
                on_retry=lambda n, delay, exc: self._log.retry(service, n, delay, exc),
            )
        finally:
            self._limiter.release(service)

    def _attempt(
        self,
        service: str,
        api_call: Callable[..., _T],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> _T:
        """Invoke ``api_call`` once, logging service/latency/outcome either way."""
        start = time.monotonic()
        try:
            result = api_call(*args, **kwargs)
        except BaseException:
            self._log.call(service, start, OUTCOME_ERROR)
            raise
        self._log.call(service, start, OUTCOME_SUCCESS)
        return result


__all__ = ["ApiGatekeeper"]
