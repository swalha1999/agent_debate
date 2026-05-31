"""Server-Sent Events (SSE) formatting helpers (task 10.3, issue #70).

PRD §6: ``GET /debates/{id}/stream`` streams a debate's live events as SSE so a
browser/CLI can render the debate round by round. This module is the tiny,
dependency-free wire-format layer: it turns a typed :class:`~agent_debate.log.
LogEvent` into one SSE record (``event: <event_type>\\ndata: <json>\\n\\n``) and
emits the terminal ``done`` sentinel that closes the stream.

No hard-coded values scattered in the route: the media type, the field labels and
the ``done`` event name live here as single named constants (guideline §7.2). The
SSE ``event`` name is the event's ``event_type`` (so consumers can dispatch on
it) and the ``data`` line is the event's JSON body — ordered + typed by contract.
"""

from __future__ import annotations

import json

from agent_debate.log import LogEvent

#: Media type a ``StreamingResponse`` must advertise for SSE (no new dependency).
SSE_MEDIA_TYPE = "text/event-stream"

#: SSE field labels (single source of truth — never inline literals).
_EVENT_FIELD = "event"
_DATA_FIELD = "data"

#: Terminal SSE event name yielded last to signal completion + close the stream.
DONE_EVENT = "done"


def format_event(name: str, data: str) -> str:
    """Render one SSE record: ``event: <name>\\ndata: <data>\\n\\n``.

    Args:
        name: The SSE event name (the event's ``event_type``, or ``done``).
        data: The already-serialised JSON ``data`` payload (single line).

    Returns:
        One complete SSE record terminated by the blank-line separator.
    """
    return f"{_EVENT_FIELD}: {name}\n{_DATA_FIELD}: {data}\n\n"


def format_log_event(event: LogEvent) -> str:
    """Render a :class:`~agent_debate.log.LogEvent` as one typed SSE record.

    The SSE ``event`` name is ``event.event_type`` and the ``data`` is the
    event's JSON serialisation, so consumers get the ordered, typed stream the
    PRD requires.
    """
    return format_event(event.event_type, event.to_jsonl())


def format_done(payload: dict[str, object]) -> str:
    """Render the terminal :data:`DONE_EVENT` record carrying ``payload`` JSON."""
    return format_event(DONE_EVENT, json.dumps(payload))


__all__ = [
    "DONE_EVENT",
    "SSE_MEDIA_TYPE",
    "format_done",
    "format_event",
    "format_log_event",
]
