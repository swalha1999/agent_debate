"""Parameter exploration over ROUNDS / MAX_WORDS / model (task 14.4, PRD §9/§10).

PRD §9 lists an *optional* exploration of how ``MAX_WORDS`` / ``ROUNDS`` / model
choice affect debate **quality and cost**; PRD §10 gives the cost-vs-scale model:
output tokens grow ~linearly in ``ROUNDS × MAX_WORDS`` while input tokens grow
**faster than linearly** in ``ROUNDS`` because every turn replays the running
context (≈ ``k₁·ROUNDS·MAX_WORDS`` output + ``k₂·ROUNDS²·MAX_WORDS`` input).

This module turns that into pure, tested functions — no new paid runs:

* :func:`empirical_points` — the observed rounds → tokens/cost/latency points
  extracted from the 14.1 :class:`RunSummary` rows.
* :func:`fit_token_model` — scale the §10 token model from one observed point.
* :func:`project_grid` — project per-cell cost across a ``rounds × max_words``
  grid, priced through the config-driven price table (Epic 15).
* :func:`model_choice_table` — price the *same* nominal usage under several
  models, exposing the model lever.

Prices come solely from the injected/loaded :class:`PriceTable` (no hard-coded
prices); the one tunable is the input:output token split, a documented constant
reflecting the §10 context-replay reasoning. Read-only — no external API calls.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from agent_debate.core.pricing import PriceTable, compute_cost
from agent_debate.core.research._summary import RunSummary
from pydantic import BaseModel, ConfigDict, Field

#: Fraction of a debate's total tokens that are *output* (completions). Debates
#: are input-heavy: every turn replays the side anchor + transcript context
#: (PRD §10), so output is the minority share. A documented modelling constant,
#: not a price — used only to split the observed combined token total.
DEFAULT_OUTPUT_FRACTION = 0.2


class EmpiricalPoint(BaseModel):
    """One observed (rounds → tokens/cost/latency) point from a real run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    rounds: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    est_cost_usd: float = Field(ge=0.0)
    avg_latency_ms: float = Field(ge=0.0)


def empirical_points(summaries: Iterable[RunSummary]) -> list[EmpiricalPoint]:
    """Extract the rounds → tokens/cost/latency points, sorted by ``rounds``.

    :param summaries: The aggregated per-run rows (14.1).
    :returns: One :class:`EmpiricalPoint` per run, ascending by round count.
    """
    points = [
        EmpiricalPoint(
            run_id=s.run_id,
            rounds=s.rounds,
            total_tokens=s.total_tokens,
            est_cost_usd=s.est_cost_usd,
            avg_latency_ms=s.avg_latency_ms,
        )
        for s in summaries
    ]
    return sorted(points, key=lambda p: p.rounds)


class TokenModel(BaseModel):
    """Scaled §10 token model: output ~linear, input ~quadratic in ``rounds``.

    ``output_tokens = out_coef · rounds · max_words`` and
    ``input_tokens  = in_coef · rounds² · max_words`` (PRD §10). The coefficients
    are scaled from one observed point so the model reproduces real data.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    out_coef: float = Field(ge=0.0)
    in_coef: float = Field(ge=0.0)

    def output_tokens(self, *, rounds: int, max_words: int) -> float:
        """Projected output tokens for a ``rounds × max_words`` configuration."""
        return self.out_coef * rounds * max_words

    def input_tokens(self, *, rounds: int, max_words: int) -> float:
        """Projected input tokens (super-linear in ``rounds`` — context replay)."""
        return self.in_coef * rounds * rounds * max_words

    def total_tokens(self, *, rounds: int, max_words: int) -> float:
        """Projected total (input + output) tokens for a configuration."""
        return self.output_tokens(rounds=rounds, max_words=max_words) + self.input_tokens(
            rounds=rounds, max_words=max_words
        )


def fit_token_model(
    points: Sequence[EmpiricalPoint],
    *,
    max_words: int,
    output_fraction: float = DEFAULT_OUTPUT_FRACTION,
) -> TokenModel | None:
    """Scale the §10 token model from the highest-round observed point.

    The combined ``total_tokens`` is split into output (``output_fraction``) and
    input (the rest); the output share is attributed to the linear term and the
    input share to the quadratic term, then divided out to recover the per-knob
    coefficients. Using the richest (most rounds) point anchors the quadratic
    term where it matters most.

    :param points: Observed empirical points (``max_words`` assumed for the fit).
    :param max_words: The ``MAX_WORDS`` the observed runs used.
    :param output_fraction: Output share of total tokens (see module constant).
    :returns: The scaled :class:`TokenModel`, or ``None`` for empty/degenerate
        input (no point, zero rounds or zero ``max_words``).
    """
    usable = [p for p in points if p.rounds > 0 and p.total_tokens > 0]
    if not usable or max_words <= 0:
        return None
    anchor = max(usable, key=lambda p: p.rounds)
    out_tokens = anchor.total_tokens * output_fraction
    in_tokens = anchor.total_tokens - out_tokens
    out_coef = out_tokens / (anchor.rounds * max_words)
    in_coef = in_tokens / (anchor.rounds * anchor.rounds * max_words)
    return TokenModel(out_coef=out_coef, in_coef=in_coef)


class GridCell(BaseModel):
    """One projected ``rounds × max_words`` cell: tokens + per-bucket USD cost."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rounds: int
    max_words: int
    input_tokens: int
    output_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float


def project_grid(
    model: TokenModel,
    *,
    rounds: Sequence[int],
    max_words: Sequence[int],
    model_id: str,
    price_table: PriceTable,
) -> list[GridCell]:
    """Project per-cell cost across the ``rounds × max_words`` grid.

    Each cell's projected input/output tokens (from ``model``) are priced
    separately through ``price_table`` so the input vs output split is explicit.

    :returns: One :class:`GridCell` per ``(rounds, max_words)`` combination.
    """
    cells: list[GridCell] = []
    for rnd in rounds:
        for words in max_words:
            inp = int(round(model.input_tokens(rounds=rnd, max_words=words)))
            out = int(round(model.output_tokens(rounds=rnd, max_words=words)))
            input_cost = compute_cost(model_id, inp, 0, price_table)
            output_cost = compute_cost(model_id, 0, out, price_table)
            cells.append(
                GridCell(
                    rounds=rnd,
                    max_words=words,
                    input_tokens=inp,
                    output_tokens=out,
                    input_cost_usd=input_cost,
                    output_cost_usd=output_cost,
                    total_cost_usd=input_cost + output_cost,
                )
            )
    return cells


class ModelCostChoice(BaseModel):
    """Same nominal usage priced under one model — the model-choice lever."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    model: str
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float


def model_choice_table(
    *,
    input_tokens: int,
    output_tokens: int,
    model_ids: Sequence[str],
    price_table: PriceTable,
) -> list[ModelCostChoice]:
    """Price one fixed ``(input, output)`` usage under each model in ``model_ids``.

    Holding the usage fixed isolates the *model* lever: the only thing that
    varies is the per-token price from ``price_table``.

    :returns: One :class:`ModelCostChoice` per model, in the order supplied.
    """
    rows: list[ModelCostChoice] = []
    for model_id in model_ids:
        input_cost = compute_cost(model_id, input_tokens, 0, price_table)
        output_cost = compute_cost(model_id, 0, output_tokens, price_table)
        rows.append(
            ModelCostChoice(
                model=model_id,
                input_cost_usd=input_cost,
                output_cost_usd=output_cost,
                total_cost_usd=input_cost + output_cost,
            )
        )
    return rows


__all__ = [
    "DEFAULT_OUTPUT_FRACTION",
    "EmpiricalPoint",
    "GridCell",
    "ModelCostChoice",
    "TokenModel",
    "empirical_points",
    "fit_token_model",
    "model_choice_table",
    "project_grid",
]
