"""Typed event schema for ``agent_debate.log`` (TASKS.md 1.2, issue #17).

:class:`LogEvent` is the Pydantic v2 model every structured log record conforms
to (PRD §5.8). Each event carries ``run_id``, ``ts``, ``round``, ``agent``,
``event_type`` and a structured ``payload``, plus optional ``tokens`` and
``latency_ms`` cost/timing fields. ``event_type`` is a strict ``Literal`` of the
seven allowed kinds (:data:`EVENT_TYPES`); any other value is rejected with a
``pydantic.ValidationError``.

:meth:`LogEvent.to_jsonl` renders one event as a single JSON line, suitable for
the per-run ``runs/<run_id>.jsonl`` sink wired by :func:`agent_debate.log.configure`
(TASKS.md 1.1). The line round-trips back through :meth:`~pydantic.BaseModel.model_validate`
to an equal model. This task is scoped to the model + serialisation only; the
``get_logger``/``log_event`` helpers land in TASKS.md 1.3.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

#: The seven allowed ``event_type`` values, in PRD §5.8 order. Single source of
#: truth: the :class:`LogEvent` ``Literal`` and dependents both read from here,
#: so the allowed set is never duplicated as a scattered inline list.
EVENT_TYPES: tuple[str, ...] = (
    "message",
    "tool_call",
    "nudge",
    "timeout",
    "retry",
    "verdict",
    "system",
)

#: The strict ``Literal`` type used by :class:`LogEvent.event_type`. Kept in
#: lock-step with :data:`EVENT_TYPES` (a mismatch is caught by the tests).
EventType = Literal[
    "message",
    "tool_call",
    "nudge",
    "timeout",
    "retry",
    "verdict",
    "system",
]


def _utc_now() -> datetime:
    """Return the current UTC time (default factory for :attr:`LogEvent.ts`)."""
    return datetime.now(tz=UTC)


class LogEvent(BaseModel):
    """A single structured log record (PRD §5.8).

    Attributes:
        run_id: Identifier of the debate run the event belongs to.
        ts: Event timestamp; defaults to the current UTC time when omitted.
        round: 1-based debate round the event occurred in.
        agent: Name/role of the agent that emitted the event (e.g. ``"pro"``).
        event_type: One of :data:`EVENT_TYPES`; any other value is rejected.
        payload: Structured, event-specific body (e.g. message text, tool args).
        tokens: Tokens consumed by the event, if applicable (else ``None``).
        latency_ms: Wall-clock latency in milliseconds, if applicable.
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str
    ts: datetime = Field(default_factory=_utc_now)
    round: int
    agent: str
    event_type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    tokens: int | None = None
    latency_ms: float | None = None

    def to_jsonl(self) -> str:
        """Serialise this event to a single JSON line for the JSONL sink.

        The returned string contains no embedded newline and round-trips back
        through :meth:`~pydantic.BaseModel.model_validate` to an equal model,
        matching the ``runs/<run_id>.jsonl`` format from TASKS.md 1.1.

        Returns:
            One line of JSON (no trailing newline).
        """
        return self.model_dump_json()
