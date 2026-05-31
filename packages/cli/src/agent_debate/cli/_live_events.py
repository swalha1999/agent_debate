"""Per-event Rich rendering for the live transcript (task 9.2, issue #65).

Split out of :mod:`._live` (guideline §3.2: split, don't compress) so each event
KIND has its own small, testable renderer and the orchestrator stays thin. The
engine streams typed :class:`~agent_debate.log.LogEvent`s whose ``event_type`` is
one of ``message | tool_call | nudge | timeout | retry | verdict | system``
(PRD §5.8); :func:`render_event` dispatches each to the matching handler and
silently ignores kinds the live human view does not surface (tool_call/retry/…).

Each handler prints via the passed Rich :class:`~rich.console.Console` the instant
it is called, so the transcript renders LIVE as events arrive — Pro/Con messages
in distinct panels, controller nudges as a distinct inline dim marker, and the
final verdict as a panel.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_debate.cli import _live_style as style
from rich.panel import Panel

if TYPE_CHECKING:
    from agent_debate.log import LogEvent
    from rich.console import Console


def _render_message(console: Console, event: LogEvent) -> None:
    """Render one debater turn as a side-coloured panel (Pro vs Con distinct)."""
    title = style.TURN_TITLE.format(
        style=style.side_style(event.agent),
        label=style.side_label(event.agent),
        round=event.round,
    )
    content = str(event.payload.get("content", ""))
    console.print(Panel(content, title=title, border_style=style.side_style(event.agent)))


def _render_nudge(console: Console, event: LogEvent) -> None:
    """Render a controller nudge as a distinct inline dim/italic marker.

    A private moderator correction (not a debate turn): shown WHERE it occurs in
    the stream, between/after the turns it followed, in a muted style so it reads
    as an aside rather than as debate content.
    """
    target = style.side_label(str(event.payload.get("target", "")))
    correction = str(event.payload.get("correction", ""))
    text = f"{style.NUDGE_LABEL} -> {target}: {correction}"
    console.print(f"[{style.NUDGE_STYLE}]{text}[/]")


def _render_verdict(console: Console, event: LogEvent) -> None:
    """Render the final verdict as a titled panel at the end of the debate."""
    winner = style.side_label(str(event.payload.get("winner", "")))
    lines = [f"{style.VERDICT_WINNER_LABEL} {winner}"]
    summary = event.payload.get("summary")
    if summary:
        lines.append(f"{style.VERDICT_SUMMARY_LABEL} {summary}")
    rationale = event.payload.get("rationale")
    if rationale:
        lines.append(f"{style.VERDICT_RATIONALE_LABEL} {rationale}")
    console.print(
        Panel(
            "\n".join(lines),
            title=style.VERDICT_TITLE,
            border_style=style.VERDICT_STYLE,
        )
    )


#: Dispatch table: ``event_type`` -> handler. Kinds absent here (tool_call,
#: timeout, retry, system) are not surfaced in the live human transcript.
_HANDLERS = {
    "message": _render_message,
    "nudge": _render_nudge,
    "verdict": _render_verdict,
}


def render_event(console: Console, event: LogEvent) -> None:
    """Render a single live event to ``console`` via its per-kind handler.

    Dispatches on ``event.event_type``; unsurfaced kinds are silently ignored so
    the live transcript stays focused on debate turns, nudges and the verdict.
    """
    handler = _HANDLERS.get(event.event_type)
    if handler is not None:
        handler(console, event)


__all__ = ["render_event"]
