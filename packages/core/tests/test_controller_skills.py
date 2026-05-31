"""Unit tests for the controller skills (TASKS.md 4.4, issue #35).

TDD red-first contract for the **controller's** three skills (PRD §5.3,
``docs/prds/anti-sycophancy.md`` §2–§4). Like the debater skills they are pure,
deterministic structuring helpers — they arrange controller-supplied content into
typed, validated outputs and never call an LLM or the network (the API gatekeeper,
Epic 13, is therefore N/A here).

Coverage:

* :func:`assess_drift` — classifies whether a debater is being *captured* (adopting
  the opponent's framing/conclusion, conceding, hedging, or restating without
  rebuttal). Flags a clearly-conceding message as ``captured`` and a firm on-side
  message as not; confidence stays within ``[0, 1]``; bad input raises.
* :func:`nudge` — builds a private correction (:class:`NudgeMessage`) that is **not**
  counted as a debate turn (``is_debate_turn is False``).
* :func:`render_verdict` — structures a :class:`Verdict` whose winner is derived from
  the supplied transcript/scores, with a rationale, **without** leaking any pre-held
  controller stance.
"""

from __future__ import annotations

import pytest
from agent_debate.core import (
    DebateSide,
    DriftAssessment,
    NudgeMessage,
    TranscriptTurn,
    Verdict,
    VerdictRequest,
    assess_drift,
    nudge,
    render_verdict,
)
from pydantic import ValidationError


def test_assess_drift_flags_conceding_message_as_captured() -> None:
    """A clearly-conceding message is classified as captured, confidence in range."""
    result = assess_drift("You're right, I agree the opponent has the stronger case.", "pro")

    assert isinstance(result, DriftAssessment)
    assert result.captured is True
    assert result.reason
    assert 0.0 <= result.confidence <= 1.0


def test_assess_drift_firm_on_side_message_is_not_captured() -> None:
    """A firm, on-side message is not classified as captured."""
    result = assess_drift(
        "That claim fails: the pro side still holds because evidence shows it.", "pro"
    )

    assert result.captured is False
    assert 0.0 <= result.confidence <= 1.0


def test_assess_drift_caller_signals_force_capture() -> None:
    """Caller-supplied signals (controller LLM heuristics) force a captured verdict."""
    result = assess_drift(
        "A neutral-sounding message.",
        "con",
        signals=["adopts_opponent_framing"],
    )

    assert result.captured is True
    assert result.confidence >= 0.5


def test_assess_drift_accepts_debate_side_enum() -> None:
    """The side may be passed as a ``DebateSide`` enum as well as a string."""
    result = assess_drift("I concede the point entirely.", DebateSide.CON)

    assert result.captured is True


def test_assess_drift_empty_message_is_rejected() -> None:
    """An empty/whitespace message fails validation before any assessment."""
    with pytest.raises(ValidationError):
        assess_drift("   ", "pro")


def test_assess_drift_bad_side_is_rejected() -> None:
    """A side outside the allowed enum values fails validation."""
    with pytest.raises(ValidationError):
        assess_drift("A message.", "sideways")


def test_drift_assessment_confidence_out_of_range_is_rejected() -> None:
    """A confidence outside ``[0, 1]`` is rejected by the output model."""
    with pytest.raises(ValidationError):
        DriftAssessment(captured=True, reason="x", confidence=1.5)


def test_drift_assessment_round_trips_through_json() -> None:
    """The structured ``DriftAssessment`` is serialisable and reloads unchanged."""
    result = assess_drift("I agree with you.", "pro")

    restored = DriftAssessment.model_validate_json(result.model_dump_json())

    assert restored == result


def test_nudge_returns_private_correction_not_counted_as_turn() -> None:
    """A nudge is a private correction that does not count as a debate turn."""
    result = nudge("pro", "Started restating the opponent without rebuttal.")

    assert isinstance(result, NudgeMessage)
    assert result.target is DebateSide.PRO
    assert result.reason
    assert result.correction  # a concrete correction instruction
    assert result.is_debate_turn is False


def test_nudge_accepts_debate_side_enum() -> None:
    """The target agent may be passed as a ``DebateSide`` enum."""
    result = nudge(DebateSide.CON, "Conceded the core claim.")

    assert result.target is DebateSide.CON


def test_nudge_empty_reason_is_rejected() -> None:
    """An empty/whitespace reason fails validation."""
    with pytest.raises(ValidationError):
        nudge("pro", "   ")


def test_nudge_bad_agent_is_rejected() -> None:
    """A target outside the allowed sides fails validation."""
    with pytest.raises(ValidationError):
        nudge("middle", "Reason.")


def test_nudge_round_trips_through_json() -> None:
    """The structured ``NudgeMessage`` is serialisable and reloads unchanged."""
    result = nudge("con", "Hedging away from the assigned side.")

    restored = NudgeMessage.model_validate_json(result.model_dump_json())

    assert restored == result


def _transcript() -> list[TranscriptTurn]:
    """Build a small two-sided transcript with per-turn scores."""
    return [
        TranscriptTurn(side="pro", text="Pro opening.", score=3.0),  # type: ignore[arg-type]
        TranscriptTurn(side="con", text="Con opening.", score=1.0),  # type: ignore[arg-type]
        TranscriptTurn(side="pro", text="Pro rebuttal.", score=2.0),  # type: ignore[arg-type]
    ]


def test_render_verdict_winner_is_derived_from_scores() -> None:
    """The winner is tallied from the supplied per-side scores, not a held opinion."""
    result = render_verdict(_transcript())

    assert isinstance(result, Verdict)
    assert result.winner is DebateSide.PRO
    assert result.rationale
    assert result.scores[DebateSide.PRO] > result.scores[DebateSide.CON]


def test_render_verdict_con_wins_when_con_outscores_pro() -> None:
    """When con's tally is higher, con is the derived winner."""
    transcript = [
        TranscriptTurn(side="pro", text="Pro.", score=1.0),  # type: ignore[arg-type]
        TranscriptTurn(side="con", text="Con.", score=4.0),  # type: ignore[arg-type]
    ]

    result = render_verdict(transcript)

    assert result.winner is DebateSide.CON


def test_render_verdict_ties_when_scores_equal() -> None:
    """Equal per-side totals produce an explicit tie, never a controller preference."""
    transcript = [
        TranscriptTurn(side="pro", text="Pro.", score=2.0),  # type: ignore[arg-type]
        TranscriptTurn(side="con", text="Con.", score=2.0),  # type: ignore[arg-type]
    ]

    result = render_verdict(transcript)

    assert result.winner == "tie"


def test_render_verdict_accepts_explicit_request_with_winner() -> None:
    """The controller LLM may supply the winner directly via a ``VerdictRequest``."""
    request = VerdictRequest(
        turns=_transcript(),
        winner="con",
        rationale="Con's evidence outweighed pro's on balance.",
    )

    result = render_verdict(request)

    assert result.winner is DebateSide.CON
    assert "Con" in result.rationale


def test_render_verdict_does_not_leak_controller_stance() -> None:
    """The verdict exposes only debate-derived fields, never a pre-held stance."""
    result = render_verdict(_transcript())

    dumped = result.model_dump()
    # 8.3 deepens the verdict with additive debate-derived fields; none expose a
    # pre-held controller stance/opinion.
    assert set(dumped) == {
        "winner",
        "rationale",
        "scores",
        "summary",
        "converged",
        "criteria_scores",
    }
    assert "stance" not in dumped
    assert "opinion" not in dumped


def test_render_verdict_empty_transcript_is_rejected() -> None:
    """An empty transcript fails validation — there is nothing to judge."""
    with pytest.raises(ValidationError):
        render_verdict([])


def test_render_verdict_round_trips_through_json() -> None:
    """The structured ``Verdict`` is serialisable and reloads unchanged."""
    result = render_verdict(_transcript())

    restored = Verdict.model_validate_json(result.model_dump_json())

    assert restored == result
