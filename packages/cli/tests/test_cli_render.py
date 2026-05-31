"""Tests for the console render helper (:func:`render_result`, task 9.1).

Covers the rendering branches the ``run`` command tests don't exercise directly:
a closing discussion, a failed-turn marker, a verdict with no summary, and a
result with no verdict yet.
"""

from __future__ import annotations

from agent_debate.cli._render import render_result
from agent_debate.core.engine.result import DebateMessage, DebateResult
from agent_debate.core.skills.models import DebateSide, Verdict


def _turn(content: str, *, failed: bool = False) -> DebateMessage:
    return DebateMessage(round=1, side=DebateSide.CON, content=content, failed=failed)


def test_render_includes_closing_and_failed_marker() -> None:
    """Closing-discussion turns render and failed turns are flagged."""
    result = DebateResult(
        topic="t",
        transcript=[_turn("opening point")],
        closing_discussion=[_turn("final word", failed=True)],
        verdict=Verdict(
            winner=DebateSide.CON,
            rationale="closed strongly",
            scores={DebateSide.PRO: 1.0, DebateSide.CON: 2.0},
        ),
    )
    text = render_result(result)
    assert "Closing discussion:" in text
    assert "final word" in text
    assert "(failed)" in text
    # No summary supplied -> no Summary line, but rationale still shows.
    assert "Summary:" not in text
    assert "Rationale: closed strongly" in text


def test_render_without_verdict() -> None:
    """A result with no verdict prints a clear ``(none)`` marker."""
    result = DebateResult(topic="t", transcript=[_turn("only point")])
    text = render_result(result)
    assert "Verdict: (none)" in text


def test_render_winner_plain_string() -> None:
    """A tie/plain-string winner (no ``.value``) renders verbatim."""
    result = DebateResult(
        topic="t",
        transcript=[_turn("p")],
        verdict=Verdict(
            winner="tie",
            rationale="evenly matched",
            scores={DebateSide.PRO: 1.0, DebateSide.CON: 1.0},
        ),
    )
    text = render_result(result)
    assert "winner=tie" in text
