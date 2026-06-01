"""Deterministic verdict scorer (TASKS.md 8.3, issue #62, #215, PRD §3.2 step 4).

Scores a debate transcript on three named criteria — ARGUMENTATION, REBUTTAL
quality, ENGAGEMENT — derived from transparent text signals (see
:mod:`agent_debate.core.skills._verdict_constants`). It judges *how* each side
argued, **never** whether a claim is true: there is NO fact-checking / truth
verification anywhere here (PRD §3). The scorer is pure and deterministic (no LLM /
network call), so the API gatekeeper (Epic 13) does not apply.

The aggregate per-side score is the weighted (differential) sum of the criteria;
the winner is the higher-scoring side. A TIE is **forbidden** (HW2 §8.3.6/§8.4/§9,
issue #215): the judge MUST always decide. The differential weights make an exact
numeric tie near-impossible, and for the rare equal-score case a deterministic
tie-breaker cascade (rebuttal quality → stayed-on-side → engagement → fixed
fallback) always yields PRO or CON — never a tie, never randomness. The debate is
reported *converged* when both sides exhibit agreement/concession signals.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_debate.core.skills._verdict_constants import (
    VERDICT_AGREEMENT_MARKERS,
    VERDICT_CONVERGED_NOTE,
    VERDICT_CONVERGENCE_MIN_SIDES,
    VERDICT_CRITERION_ARGUMENTATION,
    VERDICT_CRITERION_ENGAGEMENT,
    VERDICT_CRITERION_REBUTTAL,
    VERDICT_DECISIVE_FALLBACK_SIDE,
    VERDICT_ENGAGEMENT_MARKERS,
    VERDICT_NOT_CONVERGED_NOTE,
    VERDICT_REASONING_TEMPLATE,
    VERDICT_REBUTTAL_MARKERS,
    VERDICT_RESULT_WIN,
    VERDICT_SUMMARY_TEMPLATE,
    VERDICT_TIEBREAK_NOTE,
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
        agreement: Per-side count of agreement/concession (drift) signals — the
            tie-breaker's "stayed on side" measure (fewer is better).
        winner: The decisive winning side (PRO or CON) — never a tie (issue #215).
        decided_by: Name of the tie-breaker step that settled an equal-total
            debate, or ``None`` when the raw weighted total decided it.
        converged: ``True`` when both sides exhibited agreement/concession signals.
    """

    totals: dict[DebateSide, float]
    criteria: CriteriaScores
    agreement: dict[DebateSide, int]
    winner: DebateSide
    decided_by: str | None
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


def _side_agreement(turns: list[TranscriptTurn]) -> int:
    """Total agreement/concession (drift) signals across the side's turns."""
    return sum(_count_markers(t.text, VERDICT_AGREEMENT_MARKERS) for t in turns)


def _break_tie(
    criteria: CriteriaScores, agreement: dict[DebateSide, int]
) -> tuple[DebateSide, str]:
    """Resolve an equal-total debate deterministically (issue #215 — never a tie).

    Cascade (each step yields PRO/CON the moment it separates the sides):
    1. higher REBUTTAL quality (the most-weighted criterion / direct engagement);
    2. FEWER agreement-drift signals (the side that better stayed on its side);
    3. higher ENGAGEMENT (more direct sourcing of the opponent);
    4. a fixed deterministic FALLBACK side (symmetric transcripts only).
    """
    pro, con = DebateSide.PRO, DebateSide.CON
    cascade: tuple[tuple[str, float, float], ...] = (
        (
            VERDICT_CRITERION_REBUTTAL,
            criteria[pro][VERDICT_CRITERION_REBUTTAL],
            criteria[con][VERDICT_CRITERION_REBUTTAL],
        ),
        ("stayed-on-side", float(agreement[con]), float(agreement[pro])),
        (
            VERDICT_CRITERION_ENGAGEMENT,
            criteria[pro][VERDICT_CRITERION_ENGAGEMENT],
            criteria[con][VERDICT_CRITERION_ENGAGEMENT],
        ),
    )
    for criterion, pro_value, con_value in cascade:
        if pro_value != con_value:
            return (pro if pro_value > con_value else con, criterion)
    return (DebateSide(VERDICT_DECISIVE_FALLBACK_SIDE), VERDICT_DECISIVE_FALLBACK_SIDE)


def score_debate(turns: list[TranscriptTurn]) -> DebateScoring:
    """Score ``turns`` per side and decide a winner — never a tie (issue #215).

    Splits the transcript by side, scores each on argumentation/rebuttal/engagement
    (no fact-check), and decides the winner: the higher weighted total, or — for the
    rare equal-total case — the deterministic tie-breaker cascade (:func:`_break_tie`).
    Convergence is reported when both sides show agreement signals.

    Args:
        turns: The structured transcript turns to judge.

    Returns:
        The :class:`DebateScoring` (totals, breakdown, agreement counts, decisive
        winner, the tie-breaker step used if any, converged).
    """
    by_side: dict[DebateSide, list[TranscriptTurn]] = {DebateSide.PRO: [], DebateSide.CON: []}
    for turn in turns:
        by_side[turn.side].append(turn)
    criteria: CriteriaScores = {side: _side_criteria(rows) for side, rows in by_side.items()}
    totals = {side: sum(scores.values()) for side, scores in criteria.items()}
    agreement = {side: _side_agreement(rows) for side, rows in by_side.items()}
    gap = totals[DebateSide.PRO] - totals[DebateSide.CON]
    if gap != 0:
        winner, decided_by = (DebateSide.PRO if gap > 0 else DebateSide.CON), None
    else:
        winner, decided_by = _break_tie(criteria, agreement)
    agreed_sides = sum(1 for count in agreement.values() if count)
    converged = agreed_sides >= VERDICT_CONVERGENCE_MIN_SIDES
    return DebateScoring(
        totals=totals,
        criteria=criteria,
        agreement=agreement,
        winner=winner,
        decided_by=decided_by,
        converged=converged,
    )


def _resolve_winner(request: VerdictRequest, scoring: DebateScoring) -> DebateSide:
    """Use the controller-supplied winner verbatim, else the derived decisive side.

    A controller-supplied ``winner`` is validated through :class:`DebateSide`, so a
    tie label can never enter the verdict (issue #215 — the judge must decide).
    """
    if request.winner is not None:
        return DebateSide(request.winner)
    return scoring.winner


def _summary(winner: DebateSide, scoring: DebateScoring, turns: int) -> str:
    """Build the debate summary line — decisive result + convergence + judging note."""
    result = VERDICT_RESULT_WIN.format(winner=winner.value)
    note = VERDICT_CONVERGED_NOTE if scoring.converged else VERDICT_NOT_CONVERGED_NOTE
    return VERDICT_SUMMARY_TEMPLATE.format(turns=turns, result=result, converged=note)


def build_verdict(request: VerdictRequest) -> Verdict:
    """Assemble the deepened :class:`Verdict` from ``request`` (PRD §3.2 step 4).

    Scores the transcript on argumentation/rebuttal/engagement (no fact-checking) and
    resolves a DECISIVE winner — controller-supplied verbatim, else derived; a tie is
    impossible (issue #215). Fills the summary, convergence flag, reasoning and
    per-side breakdowns; a tie-breaker-decided outcome notes the deciding criterion. A
    controller-supplied ``rationale`` is used verbatim when present.

    Args:
        request: The validated verdict request (transcript + optional outcome).

    Returns:
        The structured :class:`Verdict` whose ``winner`` is always PRO or CON.
    """
    scoring = score_debate(request.turns)
    winner = _resolve_winner(request, scoring)
    rationale = request.rationale or VERDICT_REASONING_TEMPLATE.format(
        pro=scoring.totals[DebateSide.PRO], con=scoring.totals[DebateSide.CON], winner=winner.value
    )
    if request.rationale is None and scoring.decided_by is not None:
        rationale += VERDICT_TIEBREAK_NOTE.format(criterion=scoring.decided_by)
    return Verdict(
        winner=winner,
        rationale=rationale,
        scores=scoring.totals,
        summary=_summary(winner, scoring, len(request.turns)),
        converged=scoring.converged,
        criteria_scores=scoring.criteria,
    )


__all__ = ["CriteriaScores", "DebateScoring", "build_verdict", "score_debate"]
