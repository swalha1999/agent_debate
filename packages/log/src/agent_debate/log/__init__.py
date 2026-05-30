"""agent_debate LOG (``agent_debate.log``) — skeleton (TASKS.md 0.2 / 0.3).

The shared logging surface (PRD §5.1): structured logging, cost accounting,
the log schema and sinks. LOG is depended on by every other package. Only the
empty package shell exists for now; later tasks add the real modules.

``LIBRARY_VERSION`` / ``log_version`` are exposed so dependents can re-export
them across the workspace dependency edge, proving the wiring resolves at
runtime (TASKS.md 0.3, issue #3).

:func:`configure` (TASKS.md 1.1) is the structlog setup factory: it wires the
two sinks from PRD §5.8 — a pretty console renderer and a per-run JSONL file —
and is idempotent. It is the foundation the event-schema/helper tasks build on.

:class:`LogEvent` (TASKS.md 1.2) is the typed Pydantic v2 schema every record
conforms to; :data:`EVENT_TYPES` is the strict allowed ``event_type`` set.

:func:`get_logger`/:func:`log_event` plus the context helpers
(:func:`bind_round`/:func:`bind_context`/:func:`clear_context`) (TASKS.md 1.3)
are the ergonomic public surface dependents use to emit validated structured
events with ``run_id``/``round`` bound.
"""

from __future__ import annotations

from agent_debate.log._api import (
    bind_context,
    bind_round,
    clear_context,
    get_logger,
    log_event,
)
from agent_debate.log._setup import DEFAULT_RUNS_DIR, configure
from agent_debate.log.event import EVENT_TYPES, EventType, LogEvent

#: Version of the LOG surface; re-exported by dependents to prove the edge.
LIBRARY_VERSION = "1.00"

#: Public alias used by dependents that re-export this package's version.
log_version = LIBRARY_VERSION

__all__ = [
    "DEFAULT_RUNS_DIR",
    "EVENT_TYPES",
    "LIBRARY_VERSION",
    "EventType",
    "LogEvent",
    "bind_context",
    "bind_round",
    "clear_context",
    "configure",
    "get_logger",
    "log_event",
    "log_version",
]
