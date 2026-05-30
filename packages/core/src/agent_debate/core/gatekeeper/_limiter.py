"""In-process rate-limit check for the API gatekeeper (Epic 13, task 13.2).

A per-service sliding-window limiter: it tracks the timestamps of recent
admitted requests and refuses a new one once the count inside a window would
exceed that service's configured ceiling. Two windows are enforced —
``requests_per_minute`` and ``requests_per_hour`` — plus a concurrent counter
seam for ``concurrent_max`` (full concurrency control is task 13.4).

Every threshold comes from :class:`~agent_debate.core.gatekeeper.ServiceLimits`
(config), so no limit value is baked into Python. The only literals here are the
two window *durations* in seconds (a minute is 60s, an hour is 3600s) — unit
conversions, not rate limits — kept as named constants.

This is deliberately the *simple* check the sub-PRD scopes to 13.2. The FIFO
overflow queue (13.3) and retry/concurrency refinements (13.4) hook in at the
``ApiGatekeeper.execute`` seam; here :meth:`check_and_record` either admits a
request (recording its timestamp) or signals the exhausted window so ``execute``
can decide what to do (raise now; enqueue later).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable

from agent_debate.core.gatekeeper.config import ServiceLimits

#: Seconds in the per-minute window — a unit conversion, not a rate limit.
_MINUTE_SECONDS = 60.0

#: Seconds in the per-hour window — a unit conversion, not a rate limit.
_HOUR_SECONDS = 3600.0

#: Field name reported when the per-minute ceiling trips (matches config key).
WINDOW_PER_MINUTE = "requests_per_minute"

#: Field name reported when the per-hour ceiling trips (matches config key).
WINDOW_PER_HOUR = "requests_per_hour"


class _RateLimiter:
    """Per-service sliding-window admission check (single-process, in-memory).

    Not thread-safe by itself; the gatekeeper owns one instance and serialises
    access. ``time_fn`` is injectable so tests can advance a fake clock.
    """

    def __init__(self, *, time_fn: Callable[[], float] = time.monotonic) -> None:
        # Monotonic timestamps of admitted requests, newest last, per service.
        self._events: dict[str, deque[float]] = defaultdict(deque)
        # Live concurrent count per service (seam for 13.4 concurrency control).
        self._inflight: dict[str, int] = defaultdict(int)
        self._now = time_fn

    def check(self, service: str, limits: ServiceLimits) -> str | None:
        """Return the exhausted window name, or ``None`` if the call is allowed.

        Prunes timestamps outside each window first, then compares the live
        count to the configured ceiling. Read-only: it does *not* record the
        request, so ``execute`` can check before running and record on admit.
        """
        now = self._now()
        recent = self._events[service]
        self._prune(recent, now, _HOUR_SECONDS)
        if self._count_within(recent, now, _MINUTE_SECONDS) >= limits.requests_per_minute:
            return WINDOW_PER_MINUTE
        if len(recent) >= limits.requests_per_hour:
            return WINDOW_PER_HOUR
        return None

    def record(self, service: str) -> None:
        """Record an admitted request's timestamp against ``service``."""
        self._events[service].append(self._now())

    def at_concurrency_cap(self, service: str, limits: ServiceLimits) -> bool:
        """Return ``True`` when ``service`` already has ``concurrent_max`` in flight.

        The cap value comes from config (``limits.concurrent_max``); this only
        compares it to the live in-flight counter (the 13.4 concurrency control).
        """
        return self._inflight[service] >= limits.concurrent_max

    def in_flight(self, service: str) -> int:
        """Return ``service``'s live in-flight count (for status snapshots)."""
        return self._inflight[service]

    def acquire(self, service: str) -> None:
        """Mark one more call as in flight for ``service`` (concurrency counter)."""
        self._inflight[service] += 1

    def release(self, service: str) -> None:
        """Mark one in-flight call done for ``service`` (never below zero)."""
        if self._inflight[service] > 0:
            self._inflight[service] -= 1

    @staticmethod
    def _prune(events: deque[float], now: float, max_age: float) -> None:
        """Drop timestamps older than ``max_age`` seconds (oldest first)."""
        cutoff = now - max_age
        while events and events[0] <= cutoff:
            events.popleft()

    @staticmethod
    def _count_within(events: deque[float], now: float, window: float) -> int:
        """Count timestamps newer than ``now - window`` (assumes hour-pruned)."""
        cutoff = now - window
        return sum(1 for ts in events if ts > cutoff)


__all__ = ["WINDOW_PER_HOUR", "WINDOW_PER_MINUTE"]
