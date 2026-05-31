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

from agent_debate.core.security import validate_search_query
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


class OpponentAnalysisRequest(BaseModel):
    """Validated input for :func:`analyze_opponent_argument` (issue #34).

    Attributes:
        side: The analysing agent's assigned stance; any other value is rejected.
        opponent_message: The opponent's last message; must be non-empty after
            trimming, since there is nothing to dissect otherwise.
        weaknesses: Optional weaknesses/assumptions the agent (LLM) wants to flag;
            blanks are dropped on validation. When present, they are prioritised
            as the rebuttal target (anti-sycophancy: target and rebut, never
            concede — ``docs/prds/anti-sycophancy.md`` §2).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    side: DebateSide
    opponent_message: str = Field(min_length=1)
    weaknesses: list[str] = Field(default_factory=list)

    @field_validator("opponent_message")
    @classmethod
    def _message_non_empty(cls, value: str) -> str:
        return _strip_non_empty(value)

    @field_validator("weaknesses")
    @classmethod
    def _weaknesses_clean(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class OpponentAnalysis(BaseModel):
    """A structured dissection of the opponent's last message (issue #34).

    Attributes:
        side: The analysing agent's stance (carried through for composition).
        claims: The opponent's key claims extracted from its message.
        weaknesses: The identified weaknesses/assumptions to exploit (as flagged).
        rebuttal_target: The single prioritised point to attack next — the chosen
            strongest weakness, or the opponent's lead claim when none were flagged.
            Always non-empty so the agent rebuts rather than concedes.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    side: DebateSide
    claims: list[str]
    weaknesses: list[str]
    rebuttal_target: str


class DriftRequest(BaseModel):
    """Validated input for :func:`assess_drift` (issue #35).

    Attributes:
        message: The agent's latest message; must be non-empty after trimming.
        side: The agent's assigned side (``pro``/``con``); a bad value is rejected.
        signals: Optional drift heuristics the controller LLM flagged; blanks are
            dropped on validation.
        opponent_message: The opponent's last message, supplied as optional context
            so the deepened detector (Epic 8.1) can surface "restating the opponent
            without rebuttal" via token overlap. Backward-compatible default ``None``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    message: str = Field(min_length=1)
    side: DebateSide
    signals: list[str] = Field(default_factory=list)
    opponent_message: str | None = None

    @field_validator("message")
    @classmethod
    def _message_non_empty(cls, value: str) -> str:
        return _strip_non_empty(value)

    @field_validator("signals")
    @classmethod
    def _signals_clean(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    @field_validator("opponent_message")
    @classmethod
    def _opponent_message_clean(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class DriftAssessment(BaseModel):
    """Result of :func:`assess_drift` (anti-sycophancy §3, issue #35).

    Attributes:
        captured: ``True`` if the agent is adopting the opponent's framing/conclusion,
            conceding the core claim, hedging away from its side, or restating the
            opponent without rebuttal; ``False`` when it still defends its side.
        reason: A short human-readable explanation for the classification.
        confidence: Calibrated confidence in the classification, in ``[0, 1]``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    captured: bool
    reason: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class NudgeRequest(BaseModel):
    """Validated input for the :func:`nudge` skill's tool boundary (issue #36).

    ``nudge`` takes loose ``(agent, reason)`` params; this model gives the registered
    Pydantic AI tool (task 4.5) a single validated argument, so a bad side or an empty
    reason is rejected with a ``ValidationError`` before any correction is built.

    Attributes:
        agent: The captured agent's side (``pro``/``con``); a bad value is rejected.
        reason: Why the nudge is issued (the drift reason); non-empty after trimming.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    agent: DebateSide
    reason: str = Field(min_length=1)

    @field_validator("reason")
    @classmethod
    def _reason_non_empty(cls, value: str) -> str:
        return _strip_non_empty(value)


class NudgeMessage(BaseModel):
    """A private controller correction for a captured agent (anti-sycophancy §4).

    Per §2.4/§4 the nudge is logged and surfaced in the UI but **does not** count as
    a debate turn — :attr:`is_debate_turn` is always ``False``.

    Attributes:
        target: The side/agent being corrected.
        reason: Why the nudge was issued (the drift reason).
        correction: The private correction text re-anchoring the agent's side.
        is_debate_turn: Always ``False`` — a nudge never consumes a debate turn.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    target: DebateSide
    reason: str = Field(min_length=1)
    correction: str = Field(min_length=1)
    is_debate_turn: bool = False


class TranscriptTurn(BaseModel):
    """One turn in the transcript fed to :func:`render_verdict` (issue #35).

    Attributes:
        side: The side that produced the turn.
        text: The turn's message text (non-empty after trimming).
        score: An optional per-turn score the controller LLM assigns; the baseline
            tallies these per side to derive the winner. Defaults to ``0.0``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    side: DebateSide
    text: str = Field(min_length=1)
    score: float = 0.0

    @field_validator("text")
    @classmethod
    def _text_non_empty(cls, value: str) -> str:
        return _strip_non_empty(value)


class VerdictRequest(BaseModel):
    """Validated input for :func:`render_verdict` (issue #35).

    Attributes:
        turns: The structured transcript; at least one turn is required.
        winner: An optional controller-supplied outcome (``pro``/``con``/``tie``).
            When given it is used verbatim; otherwise the winner is tallied from the
            per-turn ``score`` totals. The controller never encodes a *pre-held*
            stance — only a debate-derived judgement (anti-sycophancy §4).
        rationale: An optional controller-supplied rationale; a tally-based rationale
            is generated when omitted.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    turns: list[TranscriptTurn] = Field(min_length=1)
    winner: DebateSide | str | None = None
    rationale: str | None = None

    @field_validator("rationale")
    @classmethod
    def _rationale_non_empty(cls, value: str | None) -> str | None:
        return None if value is None else _strip_non_empty(value)


class Verdict(BaseModel):
    """The structured outcome produced by :func:`render_verdict` (issue #35).

    The controller **never reveals its own stance** (PRD §5.3): the verdict carries
    only debate-derived fields — the winning side (or a ``tie``), a rationale, and
    the per-side score tally — never a pre-held controller opinion.

    Attributes:
        winner: The winning :class:`DebateSide`, or the tie label when neither side
            outscored the other.
        rationale: The debate-derived justification for the outcome.
        scores: The per-side score totals the outcome was derived from.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    winner: DebateSide | str
    rationale: str = Field(min_length=1)
    scores: dict[DebateSide, float]


class WebSearchInput(BaseModel):
    """Validated input for the :func:`web_search` skill (task 4.1, issue #32).

    Makes the skill tool-ready (PRD §5.2): a Pydantic model whose ``query`` field
    reuses the 7.2 trusted-boundary validator (:func:`validate_search_query`), so a
    blank / oversized / control-char query is rejected with a clear
    :class:`~agent_debate.core.security.InvalidInputError` before any provider call.

    Attributes:
        query: The web-search query; trimmed and length-capped per
            :data:`~agent_debate.core.security.MAX_QUERY_LEN`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str

    @field_validator("query")
    @classmethod
    def _check_query(cls, value: str) -> str:
        return validate_search_query(value)


__all__ = [
    "Argument",
    "ArgumentRequest",
    "DebateSide",
    "DriftAssessment",
    "DriftRequest",
    "NudgeMessage",
    "NudgeRequest",
    "OpponentAnalysis",
    "OpponentAnalysisRequest",
    "TranscriptTurn",
    "Verdict",
    "VerdictRequest",
    "WebSearchInput",
]
