"""Controller skills (TASKS.md 4.4, issue #35).

PRD §5.3 / ``docs/prds/anti-sycophancy.md`` §2–§4: the **controller** moderates the
debate. It (3) classifies each message for *drift* (capture by the opponent), (4)
privately *nudges* a captured agent back onto its side — a correction that is logged
and surfaced but **does not** count as a debate turn — and renders a structured
*verdict*. The controller **never reveals its own stance** (PRD §5.3): the verdict
declares a debate-derived outcome only.

Like the debater skills these are pure, deterministic structuring helpers: the
controller LLM supplies the judgement as arguments, the skill validates and arranges
it. No LLM/network call is made, so the API gatekeeper (Epic 13) does not apply.

Epic 8 deepens ``assess_drift`` (8.1) and ``render_verdict`` (8.3); the baselines
here (a concession-phrase heuristic; a per-side score tally) are intentionally light
and extend from the named constants in :mod:`agent_debate.core.constants`.
"""

from __future__ import annotations

from agent_debate.core.constants import (
    DRIFT_CLEAR_CONFIDENCE,
    DRIFT_CONCESSION_PHRASES,
    DRIFT_PHRASE_CONFIDENCE,
    DRIFT_REASON_CLEAR,
    DRIFT_REASON_PHRASE,
    DRIFT_REASON_SIGNALS,
    DRIFT_SIGNAL_CONFIDENCE,
    NUDGE_CORRECTION_TEMPLATE,
    VERDICT_RATIONALE_TEMPLATE,
    VERDICT_TIE,
)
from agent_debate.core.skills.models import (
    DebateSide,
    DriftAssessment,
    DriftRequest,
    NudgeMessage,
    TranscriptTurn,
    Verdict,
    VerdictRequest,
)
from agent_debate.log import get_logger
from pydantic import TypeAdapter

#: Stable ``run_id`` labels for the controller skills' standalone debug log lines. A
#: real debate binds its own run via the LOG package; these pure skills log under a
#: module label (no hard-coded value inline).
_LOG = get_logger("skills.controller")

#: Validates a raw side argument through Pydantic so a bad value raises a
#: ``ValidationError`` (consistent with the other skills' input validation), rather
#: than the bare ``ValueError`` a direct ``DebateSide(...)`` call would raise.
_SIDE_ADAPTER: TypeAdapter[DebateSide] = TypeAdapter(DebateSide)


def _detect_concession(message: str) -> str | None:
    """Return the first concession phrase found in ``message`` (lower-cased), if any."""
    lowered = message.lower()
    return next((phrase for phrase in DRIFT_CONCESSION_PHRASES if phrase in lowered), None)


def assess_drift(
    message: str,
    side: DebateSide | str,
    signals: list[str] | None = None,
) -> DriftAssessment:
    """Classify whether ``message`` shows the ``side`` agent being captured.

    Baseline (Epic 8.1 deepens this): caller-supplied ``signals`` (heuristics the
    controller LLM flagged) take precedence and force ``captured``; otherwise a
    concession-phrase scan over the text decides. Inputs are validated by
    :class:`DriftAssessment` (and :class:`DebateSide` for the side) — an empty
    message, bad side, or out-of-range confidence raises ``ValidationError``.

    Args:
        message: The agent's latest message text (must be non-empty).
        side: The agent's assigned side (``pro``/``con``).
        signals: Optional drift heuristics the controller LLM flagged.

    Returns:
        The structured :class:`DriftAssessment` (``captured``, ``reason``, ``confidence``).
    """
    resolved_side = _SIDE_ADAPTER.validate_python(side)
    request = DriftRequest(message=message, side=resolved_side, signals=signals or [])
    if request.signals:
        captured, confidence = True, DRIFT_SIGNAL_CONFIDENCE
        reason = DRIFT_REASON_SIGNALS.format(signals=", ".join(request.signals))
    elif (phrase := _detect_concession(request.message)) is not None:
        captured, confidence = True, DRIFT_PHRASE_CONFIDENCE
        reason = DRIFT_REASON_PHRASE.format(phrase=phrase)
    else:
        captured, confidence, reason = False, DRIFT_CLEAR_CONFIDENCE, DRIFT_REASON_CLEAR
    _LOG.debug("tool_call", tool="assess_drift", side=request.side.value, captured=captured)
    return DriftAssessment(captured=captured, reason=reason, confidence=confidence)


def nudge(agent: DebateSide | str, reason: str) -> NudgeMessage:
    """Build a private correction for a captured ``agent`` (anti-sycophancy §4).

    The returned :class:`NudgeMessage` re-anchors the agent's side and is logged as a
    ``nudge`` event; it is **not** a debate turn (``is_debate_turn is False``). Inputs
    are validated — a bad side or empty reason raises ``ValidationError``.

    Args:
        agent: The captured agent's side (``pro``/``con``).
        reason: Why the nudge is issued (the drift reason); must be non-empty.

    Returns:
        The structured private :class:`NudgeMessage`.
    """
    resolved = _SIDE_ADAPTER.validate_python(agent)
    trimmed = reason.strip()
    correction = NUDGE_CORRECTION_TEMPLATE.format(side=resolved.value, reason=trimmed)
    _LOG.info("nudge", tool="nudge", target=resolved.value, reason=trimmed)
    return NudgeMessage(target=resolved, reason=trimmed, correction=correction)


def _tally_scores(turns: list[TranscriptTurn]) -> dict[DebateSide, float]:
    """Sum the per-turn scores for each side (sides absent from the transcript = 0)."""
    totals: dict[DebateSide, float] = {DebateSide.PRO: 0.0, DebateSide.CON: 0.0}
    for turn in turns:
        totals[turn.side] += turn.score
    return totals


def render_verdict(transcript: VerdictRequest | list[TranscriptTurn]) -> Verdict:
    """Structure ``transcript`` into a debate-derived :class:`Verdict` (PRD §5.3).

    Accepts a bare list of turns or a :class:`VerdictRequest`. When the controller LLM
    supplies a ``winner``/``rationale`` they are used verbatim; otherwise the winner is
    tallied from the per-side score totals (a tie when equal). The verdict carries only
    debate-derived fields — never a pre-held controller stance.

    Args:
        transcript: The structured transcript, optionally with a supplied outcome.

    Returns:
        The structured :class:`Verdict` (``winner``, ``rationale``, ``scores``).
    """
    request = (
        transcript if isinstance(transcript, VerdictRequest) else VerdictRequest(turns=transcript)
    )
    scores = _tally_scores(request.turns)
    if request.winner is not None:
        winner: DebateSide | str = (
            request.winner if request.winner == VERDICT_TIE else DebateSide(request.winner)
        )
    elif scores[DebateSide.PRO] > scores[DebateSide.CON]:
        winner = DebateSide.PRO
    elif scores[DebateSide.CON] > scores[DebateSide.PRO]:
        winner = DebateSide.CON
    else:
        winner = VERDICT_TIE
    label = winner.value if isinstance(winner, DebateSide) else winner
    rationale = request.rationale or VERDICT_RATIONALE_TEMPLATE.format(
        winner=label, pro=scores[DebateSide.PRO], con=scores[DebateSide.CON]
    )
    _LOG.info("verdict", tool="render_verdict", winner=label, turns=len(request.turns))
    return Verdict(winner=winner, rationale=rationale, scores=scores)


__all__ = ["assess_drift", "nudge", "render_verdict"]
