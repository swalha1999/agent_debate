"""Typed debate output — transcript, totals, :class:`DebateResult` (issue #46).

Orchestration sub-PRD §2: a debate's **output** is a ``DebateResult`` = an ordered
transcript, per-turn tool calls, controller nudges, the closing discussion, the
final verdict, and token/cost + latency totals. This module defines that output
contract as validated, JSON-serialisable Pydantic v2 models, reusing the existing
skills models (:class:`NudgeMessage`, :class:`Verdict`, :class:`DebateSide`).

This is the engine's output **shape** only — the loop that fills it is later
Epic-6 tasks (6.2+). :class:`DebateConfig` (the input) lives in
:mod:`agent_debate.core.engine.models`.
"""

from __future__ import annotations

from typing import Any

from agent_debate.core.engine._usage import (
    UsageBreakdown,
    usage_by_agent,
    usage_by_round,
)
from agent_debate.core.pricing import CostBreakdown
from agent_debate.core.skills.models import DebateSide, NudgeMessage, Verdict
from pydantic import BaseModel, ConfigDict, Field, computed_field


class DebateMessage(BaseModel):
    """One ordered turn in a transcript or closing discussion (sub-PRD §2).

    Attributes:
        round: 1-based debate round the turn belongs to.
        side: The side that produced the turn (``pro``/``con``).
        content: The turn's message text.
        input_tokens: Prompt tokens the turn consumed (0 when unknown).
        output_tokens: Completion tokens the turn produced (0 when unknown).
        cost_usd: Estimated USD cost of the turn.
        latency_ms: Wall-clock latency of the turn, in milliseconds.
        failed: ``True`` when the turn was abandoned after its model call exhausted
            the timeout + retry budget (issue #49); a marker, not a real reply.
    """

    # ``word_count`` is a computed (read-only) field, so it appears in the JSON
    # dump; ``extra="ignore"`` lets a dumped message validate straight back
    # (the computed value is recomputed from ``content``, never stored).
    model_config = ConfigDict(frozen=True, extra="ignore")

    round: int = Field(ge=1)
    side: DebateSide
    content: str
    input_tokens: int = Field(ge=0, default=0)
    output_tokens: int = Field(ge=0, default=0)
    cost_usd: float = Field(ge=0.0, default=0.0)
    latency_ms: float = Field(ge=0.0, default=0.0)
    failed: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def word_count(self) -> int:
        """Number of whitespace-delimited words in :attr:`content`."""
        return len(self.content.split())


class ToolCallRecord(BaseModel):
    """A single tool/skill invocation made during a turn (sub-PRD §2).

    Attributes:
        round: 1-based round the call was made in.
        side: The side whose agent made the call.
        tool: Name of the tool/skill invoked (e.g. ``"search"``).
        arguments: The structured arguments passed to the tool.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    round: int = Field(ge=1)
    side: DebateSide
    tool: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class CostTotals(BaseModel):
    """Aggregate token / cost / latency totals for a run (sub-PRD §2).

    Attributes:
        input_tokens: Sum of every turn's prompt tokens.
        output_tokens: Sum of every turn's completion tokens.
        total_tokens: ``input_tokens + output_tokens``.
        cost_usd: Sum of every turn's estimated USD cost (``0.0`` until Epic 15's
            per-model price table prices the captured tokens; 6.7 only sums tokens).
        latency_ms: Sum of every turn's wall-clock latency, in milliseconds.
        by_agent: Token breakdown per side label (``pro``/``con``) — PRD §5.8.
        by_round: Token breakdown per 1-based round number — PRD §5.8.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    input_tokens: int = Field(ge=0, default=0)
    output_tokens: int = Field(ge=0, default=0)
    total_tokens: int = Field(ge=0, default=0)
    cost_usd: float = Field(ge=0.0, default=0.0)
    latency_ms: float = Field(ge=0.0, default=0.0)
    by_agent: dict[str, UsageBreakdown] = Field(default_factory=dict)
    by_round: dict[int, UsageBreakdown] = Field(default_factory=dict)

    @classmethod
    def from_messages(cls, messages: list[DebateMessage]) -> CostTotals:
        """Aggregate totals + per-agent / per-round breakdowns from each message.

        Sums the grand token/cost/latency totals and folds the same messages into
        the per-agent and per-round token breakdowns (PRD §5.8). Cost stays ``0.0``
        — Epic 15 prices the captured tokens via its per-model price table.
        """
        input_tokens = sum(m.input_tokens for m in messages)
        output_tokens = sum(m.output_tokens for m in messages)
        return cls(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=sum(m.cost_usd for m in messages),
            latency_ms=sum(m.latency_ms for m in messages),
            by_agent=usage_by_agent(messages),
            by_round=usage_by_round(messages),
        )


class DebateResult(BaseModel):
    """The structured output of one debate run (sub-PRD §2).

    Reuses :class:`NudgeMessage` and :class:`Verdict` from the skills package so
    the controller's corrections and final judgement are not re-modelled. Fully
    JSON-serialisable so the API/CLI/UI can emit a completed run unchanged.

    Attributes:
        topic: The debate topic the run argued.
        transcript: Ordered debate turns (the 10-vs-10 exchange).
        tool_calls: Per-turn tool/skill invocations.
        nudges: Private controller nudges (never debate turns; anti-sycophancy §4).
        closing_discussion: The freer closing exchange before judgement.
        verdict: The controller's final verdict, or ``None`` before judgement.
        totals: Aggregate token/cost/latency totals for the run.
        cost_breakdown: Per-model + overall cost-breakdown table (PRD §10/§11),
            priced from the config price table when the run completes; ``None``
            until the engine prices the captured tokens (Epic 15, task 15.2).
    """

    model_config = ConfigDict(extra="forbid")

    topic: str
    transcript: list[DebateMessage] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    nudges: list[NudgeMessage] = Field(default_factory=list)
    closing_discussion: list[DebateMessage] = Field(default_factory=list)
    verdict: Verdict | None = None
    totals: CostTotals = Field(default_factory=CostTotals)
    cost_breakdown: CostBreakdown | None = None


__all__ = [
    "CostBreakdown",
    "CostTotals",
    "DebateMessage",
    "DebateResult",
    "ToolCallRecord",
    "UsageBreakdown",
]
