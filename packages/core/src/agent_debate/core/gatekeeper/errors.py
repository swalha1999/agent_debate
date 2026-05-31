"""Exceptions raised by the API gatekeeper (Epic 13).

:class:`RateLimitExceededError` signals that a service's configured rate window
is exhausted at call time. It remains the signal the limiter emits when a window
is full; as of task 13.3 :meth:`~agent_debate.core.gatekeeper.ApiGatekeeper.execute`
no longer surfaces it on overflow — a limit-hit call is **enqueued** into the
FIFO overflow queue instead (sub-PRD §5). Only a genuinely **full** queue raises
:class:`QueueFullError`, the backpressure signal.
"""

from __future__ import annotations


class RateLimitExceededError(RuntimeError):
    """Raised when a service's rate window is exhausted before a call runs.

    Carries the offending ``service`` name and the human-readable ``window``
    (e.g. ``"requests_per_minute"``) so callers/logs can see which limit tripped.
    """

    def __init__(self, service: str, window: str) -> None:
        """Record the offending ``service`` and ``window`` on the error."""
        self.service = service
        self.window = window
        super().__init__(f"rate limit exceeded for service {service!r} ({window})")


class QueueFullError(RuntimeError):
    """Backpressure signal: the FIFO overflow queue is at ``queue_max_depth``.

    Raised by :meth:`~agent_debate.core.gatekeeper.ApiGatekeeper.execute` only
    when a rate-limited call cannot even be *queued* because the bounded FIFO
    queue is already full (sub-PRD §5/§7). Carries the offending ``service`` name
    and the ``max_depth`` ceiling so callers/logs can see the backpressure point.
    """

    def __init__(self, service: str, max_depth: int) -> None:
        """Record the offending ``service`` and ``max_depth`` ceiling."""
        self.service = service
        self.max_depth = max_depth
        super().__init__(f"overflow queue full for service {service!r} (max_depth={max_depth})")


__all__ = ["QueueFullError", "RateLimitExceededError"]
