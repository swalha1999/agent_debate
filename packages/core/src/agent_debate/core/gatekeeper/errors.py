"""Exceptions raised by the API gatekeeper (Epic 13).

:class:`RateLimitExceededError` signals that a service's configured rate window
is exhausted at call time. In task 13.2 this is raised by
:meth:`~agent_debate.core.gatekeeper.ApiGatekeeper.execute` *before* the wrapped
callable runs (the limit is checked first). Task 13.3 replaces the raise at the
``execute`` seam with FIFO enqueue/backpressure, but the exception type remains
the signal the limiter emits when a window is full.
"""

from __future__ import annotations


class RateLimitExceededError(RuntimeError):
    """Raised when a service's rate window is exhausted before a call runs.

    Carries the offending ``service`` name and the human-readable ``window``
    (e.g. ``"requests_per_minute"``) so callers/logs can see which limit tripped.
    """

    def __init__(self, service: str, window: str) -> None:
        self.service = service
        self.window = window
        super().__init__(f"rate limit exceeded for service {service!r} ({window})")


__all__ = ["RateLimitExceededError"]
