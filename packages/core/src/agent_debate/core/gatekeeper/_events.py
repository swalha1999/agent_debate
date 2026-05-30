"""Structured log emitters for the API gatekeeper (Epic 13).

Sub-PRD ``docs/prds/api-gatekeeper.md`` §3/§5/§7: every gatekeeper call and every
control transition (queue enqueue/drain/backpressure, retry of a transient
failure) is logged via the LOG package for monitoring. This module owns just
those emit helpers so :class:`ApiGatekeeper` stays focused on policy; it binds a
``run_id`` + ``runs_dir`` once and exposes one method per event kind.

The only literals here are logging *identifiers* (the ``agent`` label and the
``event_type`` kinds) and the milliseconds-per-second unit conversion — names and
units, never rate-limit values.
"""

from __future__ import annotations

import time
from pathlib import Path

from agent_debate.core.gatekeeper.types import CallOutcome, GatekeeperStatus
from agent_debate.log import log_event

#: ``queue_event`` tag on the on-demand queue-status snapshot event (13.5).
_STATUS_EVENT = "status"

#: ``agent`` label stamped on gatekeeper log events (a name, not a limit value).
_LOG_AGENT = "gatekeeper"

#: ``event_type`` for an external API call routed through the gatekeeper. An
#: external call maps cleanly to the LOG schema's ``tool_call`` kind (PRD §5.8).
_LOG_EVENT_TYPE = "tool_call"

#: ``event_type`` for queue lifecycle events (enqueue/drain/backpressure). These
#: are gatekeeper-internal control events, mapping to the LOG ``system`` kind.
_LOG_QUEUE_EVENT_TYPE = "system"

#: ``event_type`` stamped on each scheduled retry of a transient failure (13.4).
#: Maps to the LOG schema's dedicated ``retry`` kind (PRD §5.8).
_LOG_RETRY_EVENT_TYPE = "retry"

#: Milliseconds per second — a unit conversion for latency, not a magic number.
_MS_PER_SECOND = 1000.0


class _GatekeeperLog:
    """Emits the gatekeeper's structured events for one run (LOG package).

    Binds ``run_id`` and ``runs_dir`` once so callers pass only event-specific
    fields. One method per event kind keeps the LOG schema mapping in a single
    place.
    """

    def __init__(self, run_id: str, runs_dir: Path | str) -> None:
        self._run_id = run_id
        self._runs_dir = runs_dir

    def call(self, service: str, start: float, outcome: CallOutcome) -> None:
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

    def retry(self, service: str, retry: int, delay: float, exc: BaseException) -> None:
        """Emit one ``retry`` event for a scheduled retry of a transient failure.

        Records the 1-based ``retry`` number, the backoff ``delay`` seconds and
        the error type so repeated transient failures up to ``max_retries`` are
        observable in the run log (sub-PRD §7).
        """
        log_event(
            run_id=self._run_id,
            agent=_LOG_AGENT,
            event_type=_LOG_RETRY_EVENT_TYPE,
            round=0,
            payload={
                "service": service,
                "retry": retry,
                "delay_seconds": delay,
                "error": type(exc).__name__,
            },
            runs_dir=self._runs_dir,
        )

    def queue_event(self, service: str, queue_event: str) -> None:
        """Emit one event for a queue lifecycle transition (sub-PRD §5).

        ``queue_event`` is one of ``"enqueue"`` / ``"drain"`` / ``"backpressure"``
        so overflow pressure and backpressure are observable in the run log.
        """
        log_event(
            run_id=self._run_id,
            agent=_LOG_AGENT,
            event_type=_LOG_QUEUE_EVENT_TYPE,
            round=0,
            payload={"service": service, "queue_event": queue_event},
            runs_dir=self._runs_dir,
        )

    def status(self, status: GatekeeperStatus) -> None:
        """Emit one ``system`` event carrying the full queue-status snapshot.

        Flattens the aggregate snapshot (depth + stats, per-service + totals)
        into the event payload so the run log is a self-contained, readable
        record of queue pressure on demand (sub-PRD §3/§6).
        """
        payload = status.model_dump()
        payload["queue_event"] = _STATUS_EVENT
        log_event(
            run_id=self._run_id,
            agent=_LOG_AGENT,
            event_type=_LOG_QUEUE_EVENT_TYPE,
            round=0,
            payload=payload,
            runs_dir=self._runs_dir,
        )


__all__ = ["_GatekeeperLog"]
