"""Per-section markdown renderers for the readable run export (task 12.5).

Split from :mod:`agent_debate.core.export.markdown` so each file stays under the
150-line guideline (§3.2, split don't compress). Every helper takes part of a
completed :class:`~agent_debate.core.engine.result.DebateResult` and returns the
markdown lines for one section (transcript, closing discussion, nudges, verdict,
cost). The cost section reuses :func:`format_cost_table` verbatim — no duplicated
pricing or table markdown. None of these helpers do I/O.
"""

from __future__ import annotations

from agent_debate.core.engine.result import DebateMessage, DebateResult
from agent_debate.core.pricing import format_cost_table
from agent_debate.core.skills.models import DebateSide, NudgeMessage, Verdict


def _side_label(side: DebateSide) -> str:
    """Render a debate side as a capitalised, human-readable label (``Pro``/``Con``)."""
    return side.value.capitalize()


def _winner_label(winner: DebateSide | str) -> str:
    """Render a verdict winner (a :class:`DebateSide` or a free label like ``tie``)."""
    return _side_label(winner) if isinstance(winner, DebateSide) else str(winner)


def _turn_lines(message: DebateMessage) -> list[str]:
    """Render one transcript/closing turn as a blockquoted, attributed paragraph."""
    failed = " *(turn failed)*" if message.failed else ""
    header = f"**{_side_label(message.side)}** ({message.word_count} words){failed}"
    return [header, "", message.content, ""]


def transcript_section(messages: list[DebateMessage]) -> list[str]:
    """Render the numbered debate transcript, grouped by round (Pro then Con)."""
    if not messages:
        return ["## Transcript", "", "_No transcript recorded._", ""]
    lines = ["## Transcript", ""]
    current_round: int | None = None
    for message in messages:
        if message.round != current_round:
            current_round = message.round
            lines += [f"### Round {current_round}", ""]
        lines += _turn_lines(message)
    return lines


def closing_section(messages: list[DebateMessage]) -> list[str]:
    """Render the freer closing-discussion exchange (omitted when there is none)."""
    if not messages:
        return []
    lines = ["## Closing discussion", ""]
    for message in messages:
        lines += _turn_lines(message)
    return lines


def nudges_section(nudges: list[NudgeMessage]) -> list[str]:
    """Render the controller's private anti-sycophancy nudges (one block each)."""
    lines = ["## Controller nudges", ""]
    if not nudges:
        return lines + ["_No nudges were needed — neither agent drifted._", ""]
    for nudge in nudges:
        lines += [
            f"- **Target:** {_side_label(nudge.target)}",
            f"  - **Reason:** {nudge.reason}",
            f"  - **Correction:** {nudge.correction}",
        ]
    return lines + [""]


def verdict_section(verdict: Verdict | None) -> list[str]:
    """Render the controller's final verdict (winner, summary, rationale, scores)."""
    lines = ["## Verdict", ""]
    if verdict is None:
        return lines + ["_No verdict was rendered (e.g. every turn failed)._", ""]
    converged = "yes" if verdict.converged else "no"
    scores = ", ".join(f"{_side_label(s)} {v:g}" for s, v in verdict.scores.items())
    lines += [
        f"- **Winner:** {_winner_label(verdict.winner)}",
        f"- **Agents converged:** {converged}",
        f"- **Scores:** {scores}" if scores else "- **Scores:** _none_",
        "",
        f"**Summary.** {verdict.summary}" if verdict.summary else "**Summary.** _none_",
        "",
        f"**Rationale.** {verdict.rationale}",
        "",
    ]
    return lines


def cost_section(result: DebateResult) -> list[str]:
    """Render the token/cost section, reusing :func:`format_cost_table` verbatim."""
    totals = result.totals
    lines = [
        "## Cost & tokens",
        "",
        f"- **Total tokens:** {totals.total_tokens} "
        f"(input {totals.input_tokens}, output {totals.output_tokens})",
        f"- **Total cost:** ${totals.cost_usd:.6f}",
        f"- **Total latency:** {totals.latency_ms:.0f} ms",
        "",
    ]
    if result.cost_breakdown is None:
        return lines + ["_Cost breakdown unavailable (run not priced)._", ""]
    return lines + [format_cost_table(result.cost_breakdown), ""]


__all__ = [
    "closing_section",
    "cost_section",
    "nudges_section",
    "transcript_section",
    "verdict_section",
]
