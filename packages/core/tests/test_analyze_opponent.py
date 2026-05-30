"""Unit tests for the ``analyze_opponent_argument`` debate skill (TASKS.md 4.3, issue #34).

TDD red-first contract for the **second agent skill** (PRD §5.2): a debater calls
``analyze_opponent_argument`` as a tool to *dissect* the opponent's last message,
surface its weaknesses/assumptions, and **decide what to rebut**. Like
``build_argument`` it is a pure, deterministic structuring helper — it arranges the
agent-supplied content (the opponent message, the analysing side, and any flagged
weaknesses/claims) into a typed :class:`OpponentAnalysis`; it never calls an LLM or
the network (the API gatekeeper, Epic 13, is therefore N/A here).

Coverage:

* :class:`OpponentAnalysisRequest` — Pydantic-validated input: a non-empty
  ``opponent_message``, the analysing ``side`` constrained to the allowed values,
  and optional flagged ``weaknesses``/``claims`` the agent wants to attack.
* :class:`OpponentAnalysis` — the structured output (extracted claims, identified
  weaknesses, and a prioritised ``rebuttal_target``) reflecting the analysing side;
  it round-trips through JSON and composes into :class:`ArgumentRequest`.
* :func:`analyze_opponent_argument` — maps a valid request to the analysis;
  invalid payloads (empty message, bad side, missing field) raise
  ``ValidationError`` before any structuring happens.
"""

from __future__ import annotations

import pytest
from agent_debate.core import (
    ArgumentRequest,
    DebateSide,
    OpponentAnalysis,
    OpponentAnalysisRequest,
    analyze_opponent_argument,
    build_argument,
)
from pydantic import ValidationError


def _valid_request(**overrides: object) -> OpponentAnalysisRequest:
    """Build a valid :class:`OpponentAnalysisRequest`, overriding selected fields."""
    fields: dict[str, object] = {
        "side": "con",
        "opponent_message": "Remote work increases productivity because people focus better.",
        "weaknesses": ["Ignores collaboration costs", "No evidence for focus claim"],
    }
    fields.update(overrides)
    return OpponentAnalysisRequest(**fields)  # type: ignore[arg-type]


def test_returns_structured_analysis() -> None:
    """A valid request yields an ``OpponentAnalysis`` with claims, weaknesses, target."""
    result = analyze_opponent_argument(_valid_request())

    assert isinstance(result, OpponentAnalysis)
    assert result.claims  # at least one extracted claim
    assert result.weaknesses == ["Ignores collaboration costs", "No evidence for focus claim"]
    assert result.rebuttal_target  # a non-empty point chosen to attack


def test_analyzing_side_is_reflected() -> None:
    """The analysing side flows through onto the structured analysis."""
    pro = analyze_opponent_argument(_valid_request(side="pro"))
    con = analyze_opponent_argument(_valid_request(side="con"))

    assert pro.side is DebateSide.PRO
    assert con.side is DebateSide.CON


def test_flagged_weaknesses_are_prioritized_as_target() -> None:
    """Supplied candidate weaknesses are prioritised: the first becomes the target."""
    result = analyze_opponent_argument(
        _valid_request(weaknesses=["Strongest flaw", "Secondary flaw"])
    )

    assert result.weaknesses == ["Strongest flaw", "Secondary flaw"]
    assert result.rebuttal_target == "Strongest flaw"


def test_target_falls_back_to_claim_without_weaknesses() -> None:
    """With no flagged weaknesses, the target falls back to the opponent's claim."""
    result = analyze_opponent_argument(
        _valid_request(opponent_message="Cats are better pets than dogs.", weaknesses=[])
    )

    assert result.weaknesses == []
    assert result.rebuttal_target  # still a concrete point to rebut, never empty


def test_multiple_sentences_are_split_into_claims() -> None:
    """A multi-sentence message ending in a delimiter splits cleanly into claims."""
    result = analyze_opponent_argument(
        _valid_request(
            opponent_message="Cats are independent! Dogs need walks. They cost more?",
            weaknesses=[],
        )
    )

    assert result.claims == ["Cats are independent", "Dogs need walks", "They cost more"]
    assert result.rebuttal_target == "Cats are independent"


def test_consecutive_delimiters_do_not_yield_empty_claims() -> None:
    """Runs of punctuation and a trailing fragment never produce empty claims."""
    result = analyze_opponent_argument(
        _valid_request(opponent_message="Wait... really?! No way", weaknesses=[])
    )

    assert result.claims == ["Wait", "really", "No way"]


def test_analysis_round_trips_through_json() -> None:
    """The structured ``OpponentAnalysis`` is serialisable and reloads unchanged."""
    result = analyze_opponent_argument(_valid_request())

    restored = OpponentAnalysis.model_validate_json(result.model_dump_json())

    assert restored == result


def test_analysis_composes_into_build_argument() -> None:
    """The chosen ``rebuttal_target`` feeds ``build_argument``'s ``opponent_point``."""
    analysis = analyze_opponent_argument(_valid_request(side="con"))

    argument = build_argument(
        ArgumentRequest(
            side=analysis.side,
            claim="Remote work erodes team collaboration.",
            supports=["Fewer spontaneous exchanges"],
            opponent_point=analysis.rebuttal_target,
        )
    )

    assert argument.rebuttal is not None
    assert analysis.rebuttal_target in argument.rebuttal


def test_empty_opponent_message_is_rejected() -> None:
    """An empty/whitespace opponent message fails validation before structuring."""
    with pytest.raises(ValidationError):
        _valid_request(opponent_message="   ")


def test_bad_side_value_is_rejected() -> None:
    """A side outside the allowed enum values fails validation."""
    with pytest.raises(ValidationError):
        _valid_request(side="sideways")


def test_missing_required_field_is_rejected() -> None:
    """Omitting a required field (opponent_message) raises ``ValidationError``."""
    with pytest.raises(ValidationError):
        OpponentAnalysisRequest(side="pro")  # type: ignore[call-arg,arg-type]


def test_blank_weaknesses_are_dropped() -> None:
    """Flagged weaknesses are normalised: trimmed, with blank entries removed."""
    result = analyze_opponent_argument(
        _valid_request(weaknesses=["  Real flaw  ", "   ", "Second"])
    )

    assert result.weaknesses == ["Real flaw", "Second"]
    assert result.rebuttal_target == "Real flaw"
