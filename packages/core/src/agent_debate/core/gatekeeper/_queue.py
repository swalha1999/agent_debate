"""Bounded FIFO overflow queue for the API gatekeeper (Epic 13, task 13.3).

Sub-PRD ``docs/prds/api-gatekeeper.md`` §5: when a service's rate window is
exhausted, the request is **enqueued** here (FIFO) instead of being dropped or
crashing; a **full** queue signals backpressure; queued requests **drain** as
the windows reset. This module owns just the data structure + counters; the
admit/run/drain *policy* lives in :class:`ApiGatekeeper`.

The queue is in-process and single-threaded (the gatekeeper serialises access).
Its maximum depth comes from config (``ServiceLimits.queue_max_depth``) — no
depth literal lives here. Each pending entry captures the deferred callable and
its arguments so the gatekeeper can run it later in arrival order.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PendingCall:
    """A rate-limited call deferred into the overflow queue, with its context.

    Attributes:
        service: Service key whose window was exhausted when this was enqueued.
        api_call: The deferred external callable to run when capacity frees.
        args: Positional arguments captured for the deferred call.
        kwargs: Keyword arguments captured for the deferred call.
    """

    service: str
    api_call: Callable[..., Any]
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)


class _OverflowQueue:
    """A single bounded FIFO queue of :class:`PendingCall` entries.

    Bounded by ``max_depth`` (from config). :meth:`enqueue` appends in arrival
    order and returns ``False`` (backpressure) when full rather than dropping;
    :meth:`dequeue` pops the oldest entry. Lifetime ``enqueued_total``,
    ``drained_total`` and ``backpressure_total`` counters back :class:`QueueStatus`.
    """

    def __init__(self, max_depth: int) -> None:
        self._max_depth = max_depth
        self._items: deque[PendingCall] = deque()
        self._enqueued_total = 0
        self._drained_total = 0
        self._backpressure_total = 0

    @property
    def max_depth(self) -> int:
        """Configured maximum number of pending calls (backpressure point)."""
        return self._max_depth

    @property
    def depth(self) -> int:
        """Number of calls currently waiting in the queue."""
        return len(self._items)

    @property
    def is_full(self) -> bool:
        """``True`` when the queue has reached ``max_depth`` (backpressure)."""
        return len(self._items) >= self._max_depth

    @property
    def enqueued_total(self) -> int:
        """Lifetime count of calls that overflowed into the queue."""
        return self._enqueued_total

    @property
    def drained_total(self) -> int:
        """Lifetime count of queued calls later dequeued for execution."""
        return self._drained_total

    @property
    def backpressure_total(self) -> int:
        """Lifetime count of calls rejected because the queue was full."""
        return self._backpressure_total

    def record_backpressure(self) -> None:
        """Count one call rejected by a full queue (backpressure signal)."""
        self._backpressure_total += 1

    def enqueue(self, pending: PendingCall) -> bool:
        """Append ``pending`` in FIFO order; return ``False`` if the queue is full.

        A ``False`` return is the backpressure signal: the caller must not drop
        the request silently — it raises ``QueueFullError`` instead.
        """
        if self.is_full:
            return False
        self._items.append(pending)
        self._enqueued_total += 1
        return True

    def dequeue(self) -> PendingCall:
        """Pop and return the oldest pending call (FIFO); count it as drained."""
        pending = self._items.popleft()
        self._drained_total += 1
        return pending


__all__ = ["PendingCall"]
