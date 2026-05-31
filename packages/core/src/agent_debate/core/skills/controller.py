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

Epic 8.1 deepens ``assess_drift`` into a robust deterministic §3 drift classifier:
the scoring lives in :mod:`agent_debate.core.skills._drift_logic` with its phrase
sets/weights/threshold in :mod:`agent_debate.core.skills._drift_constants` (split
out to keep this module under the 150-line guideline). Epic 8.3 deepens
``render_verdict`` into a SUMMARY + converged/agreed flag + result + winner +
reasoning, judged on argumentation/rebuttal/engagement (NOT factual correctness —
PRD §3); its deterministic scorer + named constants live in
:mod:`agent_debate.core.skills._verdict_logic` / ``_verdict_constants``.
"""

from __future__ import annotations

from agent_debate.core.constants import (
    DRIFT_CLEAR_CONFIDENCE,
    DRIFT_REASON_SIGNALS,
    DRIFT_SIGNAL_CONFIDENCE,
    NUDGE_CORRECTION_TEMPLATE,
)
from agent_debate.core.skills._drift_constants import (
    DRIFT_CAPTURE_THRESHOLD,
    DRIFT_REASON_DETECTED,
    DRIFT_REASON_ON_SIDE,
)
from agent_debate.core.skills._drift_logic import detect_drift
from agent_debate.core.skills._verdict_logic import build_verdict
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


def _join_labels(labels: list[str]) -> str:
    """Join fired signal labels into a readable clause (``a``; ``a and b``; ``a, b and c``)."""
    if len(labels) == 1:
        return labels[0]
    return f"{', '.join(labels[:-1])} and {labels[-1]}"


def assess_drift(
    message: str,
    side: DebateSide | str,
    signals: list[str] | None = None,
    opponent_message: str | None = None,
) -> DriftAssessment:
    """Classify whether ``message`` shows the ``side`` agent being captured (§3).

    Deterministic detector (Epic 8.1): caller-supplied ``signals`` (heuristics the
    controller LLM flagged) take precedence and force ``captured`` at a high fixed
    confidence; otherwise :func:`detect_drift` scores the four anti-sycophancy §3
    signals — concession, framing/conclusion adoption, hedging, and restating the
    opponent without rebuttal — into a clamped weighted confidence. The agent is
    ``captured`` when that confidence reaches :data:`DRIFT_CAPTURE_THRESHOLD`; the
    reason names the fired signal(s). No LLM/network call is made, so the API
    gatekeeper (Epic 13) is N/A. Inputs are validated by :class:`DriftRequest` /
    :class:`DriftAssessment` (and :class:`DebateSide`) — an empty message, bad side,
    or out-of-range confidence raises ``ValidationError``.

    Args:
        message: The agent's latest message text (must be non-empty).
        side: The agent's assigned side (``pro``/``con``).
        signals: Optional drift heuristics the controller LLM flagged.
        opponent_message: The opponent's last message, optional context enabling
            the overlap-based "restating without rebuttal" signal.

    Returns:
        The structured :class:`DriftAssessment` (``captured``, ``reason``, ``confidence``).
    """
    resolved_side = _SIDE_ADAPTER.validate_python(side)
    request = DriftRequest(
        message=message,
        side=resolved_side,
        signals=signals or [],
        opponent_message=opponent_message,
    )
    if request.signals:
        captured, confidence = True, DRIFT_SIGNAL_CONFIDENCE
        reason = DRIFT_REASON_SIGNALS.format(signals=", ".join(request.signals))
    else:
        confidence, labels = detect_drift(request.message, request.opponent_message)
        captured = confidence >= DRIFT_CAPTURE_THRESHOLD
        confidence = confidence if labels else DRIFT_CLEAR_CONFIDENCE
        reason = (
            DRIFT_REASON_DETECTED.format(labels=_join_labels(labels))
            if labels
            else DRIFT_REASON_ON_SIDE
        )
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


def render_verdict(transcript: VerdictRequest | list[TranscriptTurn]) -> Verdict:
    """Structure ``transcript`` into a debate-derived :class:`Verdict` (PRD §3.2, §5.3).

    Accepts a bare list of turns or a :class:`VerdictRequest`. The deepened verdict
    (8.3) carries a SUMMARY, whether the agents CONVERGED/agreed, the RESULT (winning
    side or ``tie``), and the REASONING — judged on ARGUMENTATION / REBUTTAL quality /
    ENGAGEMENT, explicitly **not** factual correctness (PRD §3: no fact-checking). The
    transparent deterministic scoring lives in :func:`build_verdict` /
    :mod:`agent_debate.core.skills._verdict_logic`; a controller-supplied
    ``winner``/``rationale`` is honoured verbatim. The verdict carries only
    debate-derived fields — never a pre-held controller stance.

    Args:
        transcript: The structured transcript, optionally with a supplied outcome.

    Returns:
        The structured :class:`Verdict` (summary, converged, winner, rationale,
        per-side totals + per-criterion breakdown).
    """
    request = (
        transcript if isinstance(transcript, VerdictRequest) else VerdictRequest(turns=transcript)
    )
    verdict = build_verdict(request)
    label = verdict.winner.value if isinstance(verdict.winner, DebateSide) else verdict.winner
    _LOG.info("verdict", tool="render_verdict", winner=label, turns=len(request.turns))
    return verdict


__all__ = ["assess_drift", "nudge", "render_verdict"]
