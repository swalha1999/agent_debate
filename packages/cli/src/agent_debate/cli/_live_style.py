"""Named styling constants + small formatters for the live renderer (task 9.2).

No hard-coded values scattered through the render logic (guideline §7.2): every
label, colour and Rich style the live transcript uses is a NAMED constant here,
and the per-side / verdict-winner lookups go through small pure formatters. The
renderer (:mod:`._live`) and the per-event dispatch (:mod:`._live_events`) import
from here, so changing how Pro/Con/nudge/verdict look is a one-line edit.

This is terminal output (Rich), not web CSS — the global RTL/logical-property
rules do not apply; these styles only need to read clearly in a terminal.
"""

from __future__ import annotations

from agent_debate.core.skills.models import DebateSide

#: Rich style + label per debate side — Pro and Con must read DISTINCTLY.
_SIDE_STYLE: dict[str, str] = {
    DebateSide.PRO.value: "bold green",
    DebateSide.CON.value: "bold red",
}
_SIDE_LABEL: dict[str, str] = {
    DebateSide.PRO.value: "Pro",
    DebateSide.CON.value: "Con",
}

#: Fallback label/style for an unrecognised side value (defensive only).
_UNKNOWN_LABEL = "?"
_DEFAULT_STYLE = "white"

#: Round-header style and the format string for the per-side panel title.
ROUND_STYLE = "bold cyan"
TURN_TITLE = "[{style}]{label}[/] (round {round})"

#: Topic header (rendered once at the top of the live transcript).
TOPIC_STYLE = "bold magenta"
TOPIC_PREFIX = "Topic:"

#: Controller nudge — a DISTINCT dim/italic inline marker (a private moderator
#: correction, not a debate turn). Shown where it occurs in the stream.
NUDGE_STYLE = "dim italic yellow"
NUDGE_LABEL = "moderator nudge"

#: Verdict panel styling + field labels rendered at the end of the debate.
VERDICT_STYLE = "bold blue"
VERDICT_TITLE = "Verdict"
VERDICT_WINNER_LABEL = "Winner:"
VERDICT_SUMMARY_LABEL = "Summary:"
VERDICT_RATIONALE_LABEL = "Rationale:"


def side_label(side: str) -> str:
    """Return the display label (``Pro``/``Con``) for a side value."""
    return _SIDE_LABEL.get(side, _UNKNOWN_LABEL)


def side_style(side: str) -> str:
    """Return the Rich style for a side value (distinct Pro vs Con colours)."""
    return _SIDE_STYLE.get(side, _DEFAULT_STYLE)


def format_topic(topic: str) -> str:
    """Return the styled one-line topic header (Rich markup)."""
    return f"[{TOPIC_STYLE}]{TOPIC_PREFIX} {topic}[/]"


__all__ = [
    "NUDGE_LABEL",
    "NUDGE_STYLE",
    "ROUND_STYLE",
    "TURN_TITLE",
    "VERDICT_RATIONALE_LABEL",
    "VERDICT_STYLE",
    "VERDICT_SUMMARY_LABEL",
    "VERDICT_TITLE",
    "VERDICT_WINNER_LABEL",
    "format_topic",
    "side_label",
    "side_style",
]
