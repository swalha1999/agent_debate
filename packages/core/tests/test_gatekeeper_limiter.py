"""Unit tests for the gatekeeper sliding-window limiter (TASKS.md 13.2, #91).

These exercise :class:`agent_debate.core.gatekeeper._limiter._RateLimiter`
directly with an *injected fake clock* (``time_fn``) so both rate windows and
the pruning of expired timestamps are deterministically covered without
real-time sleeps:

* the **per-minute** window blocks a burst that exceeds ``requests_per_minute``;
* the **per-hour** window blocks once ``requests_per_hour`` is reached even
  though each request is spaced beyond a minute apart;
* timestamps older than the hour window are **pruned**, freeing capacity.

Thresholds come from a :class:`ServiceLimits` built in the test (config-driven),
never from code — matching the "0 hard-coded limits" guideline.
"""

from __future__ import annotations

from agent_debate.core.gatekeeper._limiter import (
    WINDOW_PER_HOUR,
    WINDOW_PER_MINUTE,
    _RateLimiter,
)
from agent_debate.core.gatekeeper.config import ServiceLimits


class _FakeClock:
    """A monotonic clock whose value the test advances explicitly."""

    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def _limits(*, per_minute: int, per_hour: int) -> ServiceLimits:
    """Build ``ServiceLimits`` with the given window ceilings (others fixed)."""
    return ServiceLimits(
        requests_per_minute=per_minute,
        requests_per_hour=per_hour,
        concurrent_max=5,
        retry_after_seconds=30,
        max_retries=3,
        queue_max_depth=100,
    )


def test_per_minute_window_blocks_burst() -> None:
    """A burst exceeding ``requests_per_minute`` trips the per-minute window."""
    clock = _FakeClock()
    limiter = _RateLimiter(time_fn=clock)
    limits = _limits(per_minute=2, per_hour=100)

    for _ in range(2):
        assert limiter.check("svc", limits) is None
        limiter.record("svc")
    assert limiter.check("svc", limits) == WINDOW_PER_MINUTE


def test_per_hour_window_blocks_spaced_requests() -> None:
    """Requests spaced > 1 min apart still trip the per-hour window at its cap."""
    clock = _FakeClock()
    limiter = _RateLimiter(time_fn=clock)
    limits = _limits(per_minute=100, per_hour=2)

    for _ in range(2):
        assert limiter.check("svc", limits) is None
        limiter.record("svc")
        clock.t += 120.0  # advance > 1 minute so per-minute never trips
    assert limiter.check("svc", limits) == WINDOW_PER_HOUR


def test_expired_timestamps_are_pruned() -> None:
    """Timestamps older than the hour window are dropped, freeing capacity."""
    clock = _FakeClock()
    limiter = _RateLimiter(time_fn=clock)
    limits = _limits(per_minute=100, per_hour=1)

    assert limiter.check("svc", limits) is None
    limiter.record("svc")
    assert limiter.check("svc", limits) == WINDOW_PER_HOUR

    clock.t += 3601.0  # advance just past the hour window -> old ts pruned
    assert limiter.check("svc", limits) is None
