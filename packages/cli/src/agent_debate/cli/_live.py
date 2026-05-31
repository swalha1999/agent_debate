"""Rich LIVE transcript renderer (task 9.2, issue #65).

PRD §6: the CLI renders the transcript LIVE as the debate happens — it consumes
:meth:`~agent_debate.core.DebateEngine.stream` (ordered, typed
:class:`~agent_debate.log.LogEvent`s, with the final
:class:`~agent_debate.core.engine.result.DebateResult` as the last item) and
renders EACH event as it arrives, never buffering to the end. This keeps the
streaming nature: one ``Console.print`` per event.

Styling is config, not magic strings: the Pro / Con / nudge / verdict labels and
colours are named constants in :mod:`._live_style` (so no hard-coded values are
scattered through the render logic), and event dispatch is split into small
per-kind helpers in :mod:`._live_events` to keep this file under the 150-line cap.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from agent_debate.cli._live_events import render_event
from agent_debate.cli._live_style import format_topic
from agent_debate.core.engine.result import DebateResult
from rich.console import Console

if TYPE_CHECKING:
    from agent_debate.log import LogEvent


def render_stream(
    topic: str,
    events: Iterator[LogEvent | DebateResult],
    *,
    console: Console | None = None,
) -> DebateResult | None:
    """Render a debate event stream LIVE, returning the final result.

    Prints a topic header, then iterates ``events`` in order, printing each
    :class:`~agent_debate.log.LogEvent` the instant it arrives (Pro/Con messages
    per round, inline controller nudges, the final verdict) so the transcript
    appears live rather than all at once. The stream's last item is the completed
    :class:`~agent_debate.core.engine.result.DebateResult`, which is captured and
    returned (not rendered as an event) so callers can still inspect the run.

    Args:
        topic: The debate topic, rendered as a header before the live events.
        events: The ordered event stream from :meth:`DebateEngine.stream`.
        console: Rich console to print to; a default one is made when ``None``.

    Returns:
        The final :class:`DebateResult`, or ``None`` if the stream ended without
        one (e.g. an empty stream).
    """
    out = console or Console()
    out.print(format_topic(topic))
    result: DebateResult | None = None
    for item in events:
        if isinstance(item, DebateResult):
            result = item
            continue
        render_event(out, item)
    return result


__all__ = ["render_stream"]
