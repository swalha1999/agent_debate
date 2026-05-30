"""Result/value types for the API gatekeeper (Epic 13).

Lightweight, frozen data types shared across the gatekeeper subpackage so the
class module, the limiter and dependents agree on one shape.

* :data:`CallOutcome` is the strict set of terminal outcomes recorded for every
  call (``"success"`` / ``"error"``); it feeds the logged ``outcome`` field.
* :class:`QueueStatus` reports one service's overflow queue depth + stats. Task
  13.2 only needs a zero-depth status (no queue yet); the FIFO queue (13.3) made
  depth/enqueued/drained real, and the full stats (13.5) add backpressure +
  in-flight — the shape is fixed here so those tasks extend rather than reshape it.
* :class:`GatekeeperStatus` is the multi-service snapshot (13.5): per-service
  :class:`QueueStatus` entries plus aggregate totals, so the run log / UI / API
  can read one JSON-serializable object covering the whole gatekeeper.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: Terminal outcome of a single ``execute`` call, logged as ``outcome``.
CallOutcome = Literal["success", "error"]

#: Value recorded for a call that completed without raising.
OUTCOME_SUCCESS: CallOutcome = "success"

#: Value recorded for a call that raised (the exception is re-raised).
OUTCOME_ERROR: CallOutcome = "error"


class QueueStatus(BaseModel):
    """Snapshot of one service's overflow queue: depth + stats (sub-PRD §3/§5).

    Attributes:
        depth: Number of requests currently waiting in the FIFO queue.
        max_depth: Configured maximum queue depth (``queue_max_depth`` from
            config), or ``None`` when unbounded / not yet wired.
        enqueued_total: Lifetime count of requests that overflowed into the queue.
        drained_total: Lifetime count of queued requests later executed.
        backpressure_total: Lifetime count of requests rejected by a full queue.
        in_flight: Live count of calls currently executing for the service.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    depth: int = Field(ge=0, default=0)
    max_depth: int | None = None
    enqueued_total: int = Field(ge=0, default=0)
    drained_total: int = Field(ge=0, default=0)
    backpressure_total: int = Field(ge=0, default=0)
    in_flight: int = Field(ge=0, default=0)


class GatekeeperStatus(BaseModel):
    """Whole-gatekeeper snapshot: per-service queues plus aggregate totals (13.5).

    JSON-serializable (``model_dump_json``) so the run log, API and SSE can ship
    it unchanged. The ``total_*`` fields sum the matching per-service counters.

    Attributes:
        services: Per-service :class:`QueueStatus` keyed by service name.
        total_depth: Sum of every service's current queue depth.
        total_enqueued: Sum of every service's lifetime enqueued count.
        total_drained: Sum of every service's lifetime drained count.
        total_backpressure: Sum of every service's lifetime backpressure count.
        total_in_flight: Sum of every service's live in-flight count.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    services: dict[str, QueueStatus] = Field(default_factory=dict)
    total_depth: int = Field(ge=0, default=0)
    total_enqueued: int = Field(ge=0, default=0)
    total_drained: int = Field(ge=0, default=0)
    total_backpressure: int = Field(ge=0, default=0)
    total_in_flight: int = Field(ge=0, default=0)

    @classmethod
    def from_services(cls, services: dict[str, QueueStatus]) -> GatekeeperStatus:
        """Build an aggregate snapshot by summing the per-service counters."""
        return cls(
            services=services,
            total_depth=sum(s.depth for s in services.values()),
            total_enqueued=sum(s.enqueued_total for s in services.values()),
            total_drained=sum(s.drained_total for s in services.values()),
            total_backpressure=sum(s.backpressure_total for s in services.values()),
            total_in_flight=sum(s.in_flight for s in services.values()),
        )


__all__ = [
    "OUTCOME_ERROR",
    "OUTCOME_SUCCESS",
    "CallOutcome",
    "GatekeeperStatus",
    "QueueStatus",
]
