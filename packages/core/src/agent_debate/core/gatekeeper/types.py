"""Result/value types for the API gatekeeper (Epic 13).

Lightweight, frozen data types shared across the gatekeeper subpackage so the
class module, the limiter and dependents agree on one shape.

* :data:`CallOutcome` is the strict set of terminal outcomes recorded for every
  call (``"success"`` / ``"error"``); it feeds the logged ``outcome`` field.
* :class:`QueueStatus` reports the overflow queue depth + stats. Task 13.2 only
  needs a zero-depth status (no queue yet); the FIFO queue (13.3) and the full
  stats (13.5) populate the remaining fields — the shape is fixed here so those
  tasks extend rather than reshape it.
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
    """Snapshot of the overflow queue's depth and counters (sub-PRD §3/§5).

    Attributes:
        depth: Number of requests currently waiting in the FIFO queue. Always
            ``0`` in task 13.2 (no queue yet); populated by 13.3.
        max_depth: Configured maximum queue depth, or ``None`` when unbounded /
            not yet wired (13.3 fills this from config).
        enqueued_total: Lifetime count of requests that overflowed into the
            queue (0 until 13.3).
        drained_total: Lifetime count of queued requests later executed (0 until
            13.3).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    depth: int = Field(ge=0, default=0)
    max_depth: int | None = None
    enqueued_total: int = Field(ge=0, default=0)
    drained_total: int = Field(ge=0, default=0)


__all__ = [
    "OUTCOME_ERROR",
    "OUTCOME_SUCCESS",
    "CallOutcome",
    "QueueStatus",
]
