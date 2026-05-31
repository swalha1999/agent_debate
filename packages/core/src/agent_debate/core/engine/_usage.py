"""Token-usage breakdown model + aggregation helpers (issue #52, task 6.7).

PRD §5.8 / §10: a run reports **token & latency per round, per agent** so Epic 15
can build the cost-breakdown table (input/output tokens × price per model). This
module defines the small, JSON-serialisable :class:`UsageBreakdown` value and the
pure aggregation helpers that fold a list of :class:`~agent_debate.core.engine.
result.DebateMessage` into per-agent and per-round breakdowns.

Split out of :mod:`result.py` so that file stays under the 150-line cap (split,
don't compress). **No prices** live here: 6.7 captures and sums *tokens* only;
pricing is task 15.1's per-model price table (Epic 15), which consumes this shape.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:  # pragma: no cover — typing-only, avoids an import cycle.
    from agent_debate.core.engine.result import DebateMessage

#: The hashable key a breakdown is grouped by (a side label or a round number).
_K = TypeVar("_K", str, int)


class UsageBreakdown(BaseModel):
    """Token totals for one slice of a run — an agent or a round (PRD §5.8).

    Attributes:
        input_tokens: Prompt tokens summed over the slice's turns.
        output_tokens: Completion tokens summed over the slice's turns.
        total_tokens: ``input_tokens + output_tokens``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    input_tokens: int = Field(ge=0, default=0)
    output_tokens: int = Field(ge=0, default=0)
    total_tokens: int = Field(ge=0, default=0)

    @classmethod
    def from_messages(cls, messages: list[DebateMessage]) -> UsageBreakdown:
        """Fold ``messages`` into a single token breakdown (input/output/total)."""
        input_tokens = sum(m.input_tokens for m in messages)
        output_tokens = sum(m.output_tokens for m in messages)
        return cls(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )


def call_tokens(output: object) -> tuple[int, int]:
    """Read ``(input_tokens, output_tokens)`` off a pydantic-ai run result.

    The installed pydantic-ai exposes usage as a ``RunUsage`` on ``result.usage``
    (an ``input_tokens`` / ``output_tokens`` pair). Read defensively via
    ``getattr`` so a model/stub without usage simply reports zero — the plumbing
    never crashes on a missing field, and real usage is captured when present.
    """
    usage = getattr(output, "usage", None)
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    return input_tokens, output_tokens


def usage_by_agent(messages: list[DebateMessage]) -> dict[str, UsageBreakdown]:
    """Group ``messages`` by their side label (``pro``/``con``) into breakdowns."""
    return _group(messages, key=lambda m: m.side.value)


def usage_by_round(messages: list[DebateMessage]) -> dict[int, UsageBreakdown]:
    """Group ``messages`` by their 1-based round number into breakdowns."""
    return _group(messages, key=lambda m: m.round)


def _group(
    messages: list[DebateMessage], *, key: Callable[[DebateMessage], _K]
) -> dict[_K, UsageBreakdown]:
    """Bucket ``messages`` by ``key`` (preserving first-seen order) → breakdowns."""
    buckets: dict[_K, list[DebateMessage]] = {}
    for message in messages:
        buckets.setdefault(key(message), []).append(message)
    return {k: UsageBreakdown.from_messages(group) for k, group in buckets.items()}


__all__ = ["UsageBreakdown", "call_tokens", "usage_by_agent", "usage_by_round"]
