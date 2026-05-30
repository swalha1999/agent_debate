"""Validated input/output models for debate skills (TASKS.md 4.2, issue #33).

PRD §5.2 lists the skills (tools) each debater exposes. ``build_argument`` is the
first one: a debater calls it to *structure* a persuasive argument or rebuttal
for its **assigned side**. These models give the skill Pydantic-validated inputs
(so a bad payload is rejected before any structuring) and a typed, serialisable
output — the shape the agent/LLM receives back to organise its turn.

* :class:`DebateSide` — the two assignable stances (``pro`` / ``con``); an
  ``str`` enum so it serialises to a plain string and a bad value fails loudly.
* :class:`ArgumentRequest` — the skill's input: the assigned ``side``, a non-empty
  ``claim``, at least one ``supports`` point, and an optional ``opponent_point``
  to rebut/link to (anti-sycophancy: the debater must rebut, not concede —
  ``docs/prds/anti-sycophancy.md`` §2).
* :class:`Argument` — the structured output: ``side``, ``claim``, normalised
  ``supports``, an optional ``rebuttal`` linking the opponent's point, and a
  ``conclusion``. Frozen + ``extra="forbid"`` to match the project's model
  hardening; it round-trips through JSON.

The skill is pure/deterministic — no LLM or network call — so the API gatekeeper
(Epic 13) does not apply; the LLM supplies the content, the skill arranges it.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DebateSide(StrEnum):
    """The stance a debater is assigned to defend (PRD §5.2)."""

    PRO = "pro"
    CON = "con"


def _strip_non_empty(value: str) -> str:
    """Strip ``value`` and reject it if nothing non-whitespace remains."""
    stripped = value.strip()
    if not stripped:
        msg = "must not be empty or whitespace-only"
        raise ValueError(msg)
    return stripped


class ArgumentRequest(BaseModel):
    """Validated input for :func:`build_argument` (the agent-supplied content).

    Attributes:
        side: The assigned stance (``pro``/``con``); any other value is rejected.
        claim: The central claim to argue; must be non-empty after trimming.
        supports: One or more supporting points; blanks are dropped on validation
            and at least one real point must remain.
        opponent_point: The opponent's last point to rebut/link to, if any.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    side: DebateSide
    claim: str = Field(min_length=1)
    supports: list[str] = Field(min_length=1)
    opponent_point: str | None = None

    @field_validator("claim")
    @classmethod
    def _claim_non_empty(cls, value: str) -> str:
        return _strip_non_empty(value)

    @field_validator("opponent_point")
    @classmethod
    def _opponent_point_non_empty(cls, value: str | None) -> str | None:
        return None if value is None else _strip_non_empty(value)

    @field_validator("supports")
    @classmethod
    def _supports_non_empty(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            msg = "at least one non-empty supporting point is required"
            raise ValueError(msg)
        return cleaned


class Argument(BaseModel):
    """A structured, persuasive argument produced by :func:`build_argument`.

    Attributes:
        side: The assigned stance this argument defends.
        claim: The central claim being argued.
        supports: The trimmed supporting points/reasons.
        rebuttal: A line linking and rebutting the opponent's point, or ``None``
            when no opponent point was supplied.
        conclusion: A closing statement reasserting the claim for the side.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    side: DebateSide
    claim: str
    supports: list[str]
    rebuttal: str | None
    conclusion: str


__all__ = ["Argument", "ArgumentRequest", "DebateSide"]
