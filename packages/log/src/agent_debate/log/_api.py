"""Public helper API for ``agent_debate.log`` (TASKS.md 1.3, issue #18).

This module ties the 1.1 setup factory (:func:`configure`) and the 1.2 event
schema (:class:`LogEvent`) into the ergonomic surface every other package uses
to emit structured events (PRD §5.8):

* :func:`get_logger` returns a structlog logger bound to ``run_id``, ensuring
  the per-run JSONL sink at ``<runs_dir>/<run_id>.jsonl`` is wired. It reuses
  the idempotent :func:`configure`, so repeat calls never duplicate sinks.
* :func:`log_event` builds and **validates** a :class:`LogEvent` (so an invalid
  ``event_type`` or a missing required field raises *before* anything reaches
  the sink) and then emits the validated record as one JSONL line.
* :func:`bind_round` / :func:`bind_context` / :func:`clear_context` push fields
  (e.g. the current ``round``) into structlog's contextvars so they propagate
  to every subsequent emission without being threaded through each call.

No external API calls are made here, so the API gatekeeper (Epic 13) does not
apply; all I/O flows through the LOG package's own sink.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from agent_debate.log._setup import DEFAULT_RUNS_DIR, configure
from agent_debate.log.event import LogEvent

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

#: Contextvar key under which the current debate round is bound.
_ROUND_KEY = "round"


def get_logger(
    run_id: str,
    *,
    runs_dir: Path | str = DEFAULT_RUNS_DIR,
) -> FilteringBoundLogger:
    """Return a structlog logger bound to ``run_id`` with the JSONL sink wired.

    Thin, ergonomic wrapper over the idempotent :func:`configure`: it guarantees
    the per-run sink at ``<runs_dir>/<run_id>.jsonl`` exists and hands back a
    logger already bound with ``run_id``. Calling it repeatedly for the same run
    neither duplicates sinks nor JSONL lines.

    Args:
        run_id: Identifier of the debate run; names the JSONL file.
        runs_dir: Directory holding per-run JSONL files (default ``"runs"``).

    Returns:
        A structlog logger pre-bound with ``run_id``.
    """
    return configure(run_id, runs_dir=runs_dir)


def bind_context(**fields: Any) -> None:
    """Bind ``fields`` into structlog's contextvars for later emissions.

    Bound fields (e.g. ``round``/``agent``) merge into every event emitted
    afterwards on this context, so callers need not thread them through each
    :func:`log_event` call.
    """
    structlog.contextvars.bind_contextvars(**fields)


def bind_round(round_: int) -> None:
    """Bind the current debate ``round`` so it propagates to later events."""
    bind_context(**{_ROUND_KEY: round_})


def clear_context() -> None:
    """Clear all contextvars bound via :func:`bind_context`/:func:`bind_round`."""
    structlog.contextvars.clear_contextvars()


def log_event(
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
    """Validate fields via :class:`LogEvent` and emit one JSONL record.

    The ``LogEvent`` is constructed (and thus validated) *first*: an unknown
    ``event_type`` or a missing required field raises a ``ValidationError``
    before anything is written, so the sink never sees a malformed record. The
    ``round`` falls back to the contextvar bound via :func:`bind_round` when not
    passed explicitly; an explicit value always wins.

    Args:
        run_id: Identifier of the debate run.
        agent: Name/role of the emitting agent.
        event_type: One of the allowed ``EVENT_TYPES``.
        round: 1-based round; defaults to the bound contextvar round.
        payload: Structured, event-specific body.
        tokens: Tokens consumed, if applicable.
        latency_ms: Wall-clock latency in milliseconds, if applicable.
        runs_dir: Directory holding per-run JSONL files.

    Returns:
        The validated :class:`LogEvent` that was emitted.
    """
    # Build kwargs as a plain dict so pydantic (not mypy) is the single point of
    # validation: a missing round / unknown event_type raises before any emit.
    fields: dict[str, Any] = {
        "run_id": run_id,
        "agent": agent,
        "event_type": event_type,
        "payload": payload if payload is not None else {},
        "tokens": tokens,
        "latency_ms": latency_ms,
    }
    effective_round = _resolve_round(round)
    if effective_round is not None:
        fields["round"] = effective_round
    event = LogEvent(**fields)
    logger = get_logger(run_id, runs_dir=runs_dir)
    logger.info(
        event_type,
        run_id=event.run_id,
        round=event.round,
        agent=event.agent,
        event_type=event.event_type,
        payload=event.payload,
        tokens=event.tokens,
        latency_ms=event.latency_ms,
    )
    return event


def _resolve_round(explicit: int | None) -> int | None:
    """Return ``explicit`` round, else the contextvar-bound round (or ``None``)."""
    if explicit is not None:
        return explicit
    bound = structlog.contextvars.get_contextvars().get(_ROUND_KEY)
    return bound if isinstance(bound, int) else None
