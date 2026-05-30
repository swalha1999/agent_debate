"""Unit tests for the ``build_argument`` debate skill (TASKS.md 4.2, issue #33).

TDD red-first contract for the **first agent skill** (PRD §5.2): a debater calls
``build_argument`` as a tool to *structure* a persuasive argument or rebuttal for
its assigned side. The skill is a pure, deterministic structuring helper — it
takes the agent-supplied content (side, claim, supports, opponent point) and
arranges it into a typed :class:`Argument`; it never calls an LLM or the network
(the API gatekeeper, Epic 13, is therefore N/A here).

Coverage:

* :class:`ArgumentRequest` — Pydantic-validated input: a ``side`` constrained to
  the allowed values, a non-empty ``claim``, ``supports`` and an optional
  ``opponent_point`` to rebut/link to.
* :class:`Argument` — the structured output (claim, supports, link/rebuttal,
  conclusion) reflecting the assigned side; it round-trips through JSON.
* :func:`build_argument` — maps a valid request to a structured ``Argument``;
  invalid payloads (empty claim, bad side, missing required field) raise
  ``ValidationError`` before any structuring happens.
"""

from __future__ import annotations

import pytest
from agent_debate.core import (
    Argument,
    ArgumentRequest,
    DebateSide,
    build_argument,
)
from pydantic import ValidationError


def _valid_request(**overrides: object) -> ArgumentRequest:
    """Build a valid :class:`ArgumentRequest`, overriding selected fields."""
    fields: dict[str, object] = {
        "side": "pro",
        "claim": "Remote work increases productivity.",
        "supports": ["Fewer commute hours", "Quieter focus time"],
    }
    fields.update(overrides)
    return ArgumentRequest(**fields)  # type: ignore[arg-type]


def test_build_argument_returns_structured_argument() -> None:
    """A valid request yields an ``Argument`` with all structured fields."""
    result = build_argument(_valid_request())

    assert isinstance(result, Argument)
    assert result.claim == "Remote work increases productivity."
    assert result.supports == ["Fewer commute hours", "Quieter focus time"]
    assert result.conclusion  # a non-empty concluding statement
    assert result.rebuttal is None  # no opponent point given


def test_side_is_reflected_in_the_argument() -> None:
    """The assigned side flows through onto the structured ``Argument``."""
    pro = build_argument(_valid_request(side="pro"))
    con = build_argument(_valid_request(side="con"))

    assert pro.side is DebateSide.PRO
    assert con.side is DebateSide.CON


def test_opponent_point_produces_a_rebuttal_link() -> None:
    """When given an opponent point, the output links/rebuts it (anti-sycophancy)."""
    result = build_argument(_valid_request(opponent_point="Remote work harms collaboration."))

    assert result.rebuttal is not None
    assert "Remote work harms collaboration." in result.rebuttal


def test_argument_round_trips_through_json() -> None:
    """The structured ``Argument`` is serialisable and reloads unchanged."""
    result = build_argument(_valid_request(opponent_point="It hurts mentorship."))

    restored = Argument.model_validate_json(result.model_dump_json())

    assert restored == result


def test_empty_claim_is_rejected() -> None:
    """An empty/whitespace claim fails validation before structuring."""
    with pytest.raises(ValidationError):
        _valid_request(claim="   ")


def test_bad_side_value_is_rejected() -> None:
    """A side outside the allowed enum values fails validation."""
    with pytest.raises(ValidationError):
        _valid_request(side="sideways")


def test_missing_required_field_is_rejected() -> None:
    """Omitting a required field (claim) raises ``ValidationError``."""
    with pytest.raises(ValidationError):
        ArgumentRequest(side="pro", supports=["x"])  # type: ignore[call-arg,arg-type]


def test_empty_supports_is_rejected() -> None:
    """At least one supporting point is required to structure an argument."""
    with pytest.raises(ValidationError):
        _valid_request(supports=[])


def test_all_blank_supports_is_rejected() -> None:
    """Supports that are present but all blank are rejected after normalisation."""
    with pytest.raises(ValidationError):
        _valid_request(supports=["   ", "\t"])


def test_supports_are_stripped_and_blanks_dropped() -> None:
    """Supporting points are normalised: trimmed, with blank entries removed."""
    result = build_argument(_valid_request(supports=["  Padded point  ", "   ", "Second"]))

    assert result.supports == ["Padded point", "Second"]
