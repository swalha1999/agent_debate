"""Deterministic verdict scorer (TASKS.md 8.3, issue #62, PRD §3.2 step 4).

Scores a debate transcript on three named criteria — ARGUMENTATION, REBUTTAL
quality, ENGAGEMENT — derived from transparent text signals (see
:mod:`agent_debate.core.skills._verdict_constants`). It judges *how* each side
argued, **never** whether a claim is true: there is NO fact-checking / truth
verification anywhere here (PRD §3). The scorer is pure and deterministic (no LLM /
network call), so the API gatekeeper (Epic 13) does not apply.

The aggregate per-side score is the weighted sum of the criteria; the winner is the
higher-scoring side, or a TIE when the gap is within
:data:`~agent_debate.core.skills._verdict_constants.VERDICT_TIE_MARGIN`. The debate
is reported *converged* when both sides exhibit agreement/concession signals.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_debate.core.constants import VERDICT_TIE
from agent_debate.core.skills._verdict_constants import (
    VERDICT_AGREEMENT_MARKERS,
    VERDICT_CONVERGED_NOTE,
    VERDICT_CONVERGENCE_MIN_SIDES,
    VERDICT_CRITERION_ARGUMENTATION,
    VERDICT_CRITERION_ENGAGEMENT,
    VERDICT_CRITERION_REBUTTAL,
    VERDICT_ENGAGEMENT_MARKERS,
    VERDICT_NOT_CONVERGED_NOTE,
    VERDICT_REASONING_TEMPLATE,
    VERDICT_REBUTTAL_MARKERS,
    VERDICT_RESULT_TIE,
    VERDICT_RESULT_WIN,
    VERDICT_SUMMARY_TEMPLATE,
    VERDICT_TIE_MARGIN,
    VERDICT_WEIGHT_ARGUMENTATION,
    VERDICT_WEIGHT_ENGAGEMENT,
    VERDICT_WEIGHT_REBUTTAL,
)
from agent_debate.core.skills.models import (
    DebateSide,
    TranscriptTurn,
    Verdict,
    VerdictRequest,
)

#: Per-side per-criterion score breakdown (``{side: {criterion: score}}``).
CriteriaScores = dict[DebateSide, dict[str, float]]


@dataclass(frozen=True, slots=True)
class DebateScoring:
    """The deterministic scoring of a transcript (the scorer's full output).

    Attributes:
        totals: The aggregate weighted score per side.
        criteria: The per-criterion breakdown per side (argumentation/rebuttal/
            engagement).
        winner: The higher-scoring side, or ``None`` when within the tie margin.
        converged: ``True`` when both sides exhibited agreement/concession signals.
    """

    totals: dict[DebateSide, float]
    criteria: CriteriaScores
    winner: DebateSide | None
    converged: bool


def _count_markers(text: str, markers: tuple[str, ...]) -> int:
    """Count how many of ``markers`` appear in ``text`` (case-insensitive)."""
    lowered = text.lower()
    return sum(1 for marker in markers if marker in lowered)


def _side_criteria(turns: list[TranscriptTurn]) -> dict[str, float]:
    """Score one side's ``turns`` on the three named criteria (argument quality only).

    Argumentation = the per-turn base weight plus any controller-supplied per-turn
    ``score`` (so an explicit LLM tally still counts); rebuttal/engagement are the
    transparent text-signal counts. None of this inspects whether a claim is *true*.
    """
    argumentation = sum(VERDICT_WEIGHT_ARGUMENTATION + t.score for t in turns)
    rebuttal = sum(_count_markers(t.text, VERDICT_REBUTTAL_MARKERS) for t in turns)
    engagement = sum(_count_markers(t.text, VERDICT_ENGAGEMENT_MARKERS) for t in turns)
    return {
        VERDICT_CRITERION_ARGUMENTATION: argumentation,
        VERDICT_CRITERION_REBUTTAL: rebuttal * VERDICT_WEIGHT_REBUTTAL,
        VERDICT_CRITERION_ENGAGEMENT: engagement * VERDICT_WEIGHT_ENGAGEMENT,
    }


def _side_agreed(turns: list[TranscriptTurn]) -> bool:
    """``True`` when any of the side's turns carry an agreement/concession signal."""
    return any(_count_markers(t.text, VERDICT_AGREEMENT_MARKERS) for t in turns)


def score_debate(turns: list[TranscriptTurn]) -> DebateScoring:
    """Score ``turns`` per side on argumentation/rebuttal/engagement (no fact-check).

    Splits the transcript by side, scores each side's text on the three named
    criteria, and derives the winner (higher total; ``None`` within the tie margin)
    and whether the agents converged (both sides showing agreement signals).

    Args:
        turns: The structured transcript turns to judge.

    Returns:
        The :class:`DebateScoring` (totals, per-criterion breakdown, winner, converged).
    """
    by_side: dict[DebateSide, list[TranscriptTurn]] = {DebateSide.PRO: [], DebateSide.CON: []}
    for turn in turns:
        by_side[turn.side].append(turn)
    criteria: CriteriaScores = {side: _side_criteria(rows) for side, rows in by_side.items()}
    totals = {side: sum(scores.values()) for side, scores in criteria.items()}
    gap = totals[DebateSide.PRO] - totals[DebateSide.CON]
    if abs(gap) <= VERDICT_TIE_MARGIN:
        winner: DebateSide | None = None
    else:
        winner = DebateSide.PRO if gap > 0 else DebateSide.CON
    agreed_sides = sum(1 for rows in by_side.values() if _side_agreed(rows))
    converged = agreed_sides >= VERDICT_CONVERGENCE_MIN_SIDES
    return DebateScoring(totals=totals, criteria=criteria, winner=winner, converged=converged)


def _resolve_winner(request: VerdictRequest, scoring: DebateScoring) -> DebateSide | str:
    """Use the controller-supplied winner verbatim, else the derived/tie outcome."""
    if request.winner is not None:
        return request.winner if request.winner == VERDICT_TIE else DebateSide(request.winner)
    return scoring.winner if scoring.winner is not None else VERDICT_TIE


def _winner_label(winner: DebateSide | str) -> str:
    """Plain string label for a side or the tie marker."""
    return winner.value if isinstance(winner, DebateSide) else winner


def _summary(winner: DebateSide | str, scoring: DebateScoring, turns: int) -> str:
    """Build the debate summary line — result + convergence + judging note."""
    result = (
        VERDICT_RESULT_TIE
        if winner == VERDICT_TIE
        else VERDICT_RESULT_WIN.format(winner=_winner_label(winner))
    )
    note = VERDICT_CONVERGED_NOTE if scoring.converged else VERDICT_NOT_CONVERGED_NOTE
    return VERDICT_SUMMARY_TEMPLATE.format(turns=turns, result=result, converged=note)


def build_verdict(request: VerdictRequest) -> Verdict:
    """Assemble the deepened :class:`Verdict` from ``request`` (PRD §3.2 step 4).

    Scores the transcript on argumentation/rebuttal/engagement (no fact-checking),
    resolves the winner (controller-supplied verbatim, else derived; tie within the
    margin), and fills the summary, convergence flag, reasoning and per-side
    breakdowns. A controller-supplied ``rationale`` is used verbatim when present.

    Args:
        request: The validated verdict request (transcript + optional outcome).

    Returns:
        The structured :class:`Verdict`.
    """
    scoring = score_debate(request.turns)
    winner = _resolve_winner(request, scoring)
    label = _winner_label(winner)
    rationale = request.rationale or VERDICT_REASONING_TEMPLATE.format(
        pro=scoring.totals[DebateSide.PRO], con=scoring.totals[DebateSide.CON], winner=label
    )
    return Verdict(
        winner=winner,
        rationale=rationale,
        scores=scoring.totals,
        summary=_summary(winner, scoring, len(request.turns)),
        converged=scoring.converged,
        criteria_scores=scoring.criteria,
    )


__all__ = ["CriteriaScores", "DebateScoring", "build_verdict", "score_debate"]
