"""Cost-breakdown table — tokens × price → cost, per model + overall (task 15.2).

PRD §10/§11: a run's token totals become a **cost-breakdown table** — per-model
rows (input/output tokens × the per-model price) plus an overall total, and an
aggregate across runs. This module ships the typed, JSON-serialisable
:class:`CostBreakdown` / :class:`ModelCostRow` value objects and the pure builders
that price a :class:`~agent_debate.core.engine.result.DebateResult` from a
config-driven :class:`~agent_debate.core.pricing.config.PriceTable`.

"0 hard-coded prices": every dollar figure flows from :func:`compute_cost`, which
reads the price table (file or injected). The markdown renderer lives next door in
:mod:`agent_debate.core.pricing._format`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

from agent_debate.core.pricing._cost import compute_cost
from agent_debate.core.pricing.config import PriceTable
from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:  # pragma: no cover — typing-only, avoids an import cycle.
    from agent_debate.core.engine.result import DebateResult
    from agent_debate.core.skills.models import DebateSide


class ModelCostRow(BaseModel):
    """One per-model row of the cost-breakdown table (PRD §10).

    Attributes:
        model: The ``provider:model`` id the tokens were billed against.
        input_tokens: Prompt tokens summed over every turn on this model.
        output_tokens: Completion tokens summed over every turn on this model.
        input_cost: USD cost of the input tokens (tokens × the table input price).
        output_cost: USD cost of the output tokens.
        total_cost: ``input_cost + output_cost``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    model: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    input_cost: float = Field(ge=0.0)
    output_cost: float = Field(ge=0.0)
    total_cost: float = Field(ge=0.0)


class CostBreakdown(BaseModel):
    """A run's (or aggregate's) cost-breakdown table (PRD §10/§11).

    Attributes:
        rows: One :class:`ModelCostRow` per distinct model, ordered by first use.
        input_tokens: Grand input tokens across every row.
        output_tokens: Grand output tokens across every row.
        total_cost: Grand USD cost (sum of every row's ``total_cost``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    rows: list[ModelCostRow] = Field(default_factory=list)
    input_tokens: int = Field(ge=0, default=0)
    output_tokens: int = Field(ge=0, default=0)
    total_cost: float = Field(ge=0.0, default=0.0)


def _per_model_tokens(
    result: DebateResult, side_models: Mapping[DebateSide, str]
) -> dict[str, tuple[int, int]]:
    """Fold every turn's tokens into ``model -> (input_tokens, output_tokens)``.

    Each turn's :attr:`~...result.DebateMessage.side` resolves to a model via
    ``side_models`` (the run config's per-side model ids); sides sharing a model
    merge into one bucket. Insertion order is preserved for stable table rows.
    """
    buckets: dict[str, tuple[int, int]] = {}
    for message in result.transcript + result.closing_discussion:
        model = side_models[message.side]
        prev_in, prev_out = buckets.get(model, (0, 0))
        buckets[model] = (prev_in + message.input_tokens, prev_out + message.output_tokens)
    return buckets


def _row(model: str, tokens: tuple[int, int], price_table: PriceTable) -> ModelCostRow:
    """Price one ``model``'s ``(input, output)`` tokens into a :class:`ModelCostRow`."""
    input_tokens, output_tokens = tokens
    input_cost = compute_cost(model, input_tokens, 0, price_table)
    output_cost = compute_cost(model, 0, output_tokens, price_table)
    return ModelCostRow(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=input_cost + output_cost,
    )


def _from_rows(rows: list[ModelCostRow]) -> CostBreakdown:
    """Assemble a :class:`CostBreakdown` (grand totals re-summed from ``rows``)."""
    return CostBreakdown(
        rows=rows,
        input_tokens=sum(r.input_tokens for r in rows),
        output_tokens=sum(r.output_tokens for r in rows),
        total_cost=sum(r.total_cost for r in rows),
    )


def cost_breakdown_from_result(
    result: DebateResult,
    *,
    side_models: Mapping[DebateSide, str],
    price_table: PriceTable,
) -> CostBreakdown:
    """Build a per-model + overall :class:`CostBreakdown` for one debate run.

    Maps each turn's side to its model (``side_models``), sums tokens per model,
    and prices them through ``price_table`` (tokens × per-model price → USD).
    """
    buckets = _per_model_tokens(result, side_models)
    return _from_rows([_row(model, tokens, price_table) for model, tokens in buckets.items()])


def aggregate_costs(breakdowns: Iterable[CostBreakdown]) -> CostBreakdown:
    """Sum many runs' breakdowns into one aggregate (per-model rows + overall).

    Rows for the same model are merged across runs; per-model and grand totals are
    re-summed so the aggregate reads exactly like a single run's table (PRD §11).
    """
    merged: dict[str, ModelCostRow] = {}
    for breakdown in breakdowns:
        for row in breakdown.rows:
            existing = merged.get(row.model)
            merged[row.model] = row if existing is None else _add_rows(existing, row)
    return _from_rows(list(merged.values()))


def _add_rows(left: ModelCostRow, right: ModelCostRow) -> ModelCostRow:
    """Field-wise sum of two rows for the same model (used by aggregation)."""
    return ModelCostRow(
        model=left.model,
        input_tokens=left.input_tokens + right.input_tokens,
        output_tokens=left.output_tokens + right.output_tokens,
        input_cost=left.input_cost + right.input_cost,
        output_cost=left.output_cost + right.output_cost,
        total_cost=left.total_cost + right.total_cost,
    )


__all__ = [
    "CostBreakdown",
    "ModelCostRow",
    "aggregate_costs",
    "cost_breakdown_from_result",
]
