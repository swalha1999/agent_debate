"""Live event streaming primitives for the LOG package (issue #51, task 6.6).

The engine must YIELD its events (``message | tool_call | nudge | timeout |
retry | verdict | system``) live so CLI/API/UI can render as they happen
(orchestration §6) — in addition to logging them to ``runs/<run_id>.jsonl``.

The streamed event IS the LOG event (:class:`~agent_debate.log.LogEvent`): one
typed, JSON-serialisable schema for both the log and the stream. These primitives
live here, alongside :func:`~agent_debate.log.log_event`, so there is a single
build+log+emit chokepoint (:func:`emit_event`) that consumers across packages
(engine, word-limit enforcer, …) share without a layering inversion:

* :class:`EventSink` — the typed consumer protocol (receives each ``LogEvent``).
* :class:`CollectingSink` — the simplest sink: appends events to a list.
* :func:`emit_event` — logs an event via :func:`log_event` AND forwards the SAME
  validated record to an optional sink (``None`` = log-only, backward compatible).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from agent_debate.log._api import log_event
from agent_debate.log._setup import DEFAULT_RUNS_DIR
from agent_debate.log.event import LogEvent


class EventSink(Protocol):
    """A consumer that receives engine events live, in the order they happen.

    The single call is invoked with each validated :class:`~agent_debate.log.
    LogEvent` the moment it is logged, so CLI/API/UI can render the debate as it
    unfolds. Implementations must not block the producer for long.
    """

    def __call__(self, event: LogEvent) -> None:
        """Receive one ordered, typed event."""


class CollectingSink:
    """An :class:`EventSink` that appends every received event to a list.

    The simplest live consumer: useful for tests and for callers that want the
    ordered, complete event sequence after a run without managing a thread.
    """

    def __init__(self) -> None:
        self.events: list[LogEvent] = []

    def __call__(self, event: LogEvent) -> None:
        """Append ``event`` to :attr:`events` in arrival order."""
        self.events.append(event)


def emit_event(
    sink: EventSink | None,
    *,
    run_id: str,
    agent: str,
    event_type: str,
    round: int | None = None,  # noqa: A002 — matches LogEvent's field name.
    payload: dict[str, Any] | None = None,
    tokens: int | None = None,
    latency_ms: float | None = None,
    runs_dir: Path | str = DEFAULT_RUNS_DIR,
) -> LogEvent:
    """Log one event via :func:`log_event` AND stream it to ``sink`` (single point).

    The DRY chokepoint replacing bare :func:`log_event` calls on the live path: the
    event is built + validated + written to the JSONL sink exactly as before, and
    the SAME validated :class:`~agent_debate.log.LogEvent` is forwarded to ``sink``
    when one is given. With ``sink=None`` the behaviour is identical to a bare
    ``log_event`` call (backward compatible).

    Args:
        sink: The optional live consumer; ``None`` disables streaming.
        run_id: Identifier of the debate run.
        agent: Name/role of the emitting agent.
        event_type: One of :data:`~agent_debate.log.EVENT_TYPES`.
        round: 1-based round; defaults to the bound contextvar round.
        payload: Structured, event-specific body.
        tokens: Tokens consumed, if applicable.
        latency_ms: Wall-clock latency in milliseconds, if applicable.
        runs_dir: Directory holding per-run JSONL files.

    Returns:
        The validated :class:`~agent_debate.log.LogEvent` that was logged (and
        streamed).
    """
    event = log_event(
        run_id=run_id,
        agent=agent,
        event_type=event_type,
        round=round,
        payload=payload,
        tokens=tokens,
        latency_ms=latency_ms,
        runs_dir=runs_dir,
    )
    if sink is not None:
        sink(event)
    return event


__all__ = ["CollectingSink", "EventSink", "emit_event"]
