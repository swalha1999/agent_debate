"""Tests for the parameter-exploration functions (issue #100, task 14.4, PRD §9/§10).

TDD-first: pin the 14.4 contract — pure functions that turn the 14.1
:class:`RunSummary` rows + the config-driven price table into a
parameter-exploration over ``MAX_WORDS`` / ``ROUNDS`` / model:

* :func:`empirical_points` — the observed rounds → tokens/cost/latency points.
* :func:`fit_token_model` / :func:`project_grid` — project cost across a
  ``rounds × max_words`` grid from the §10 token model (output ~linear, input
  ~quadratic in rounds), so doubling rounds roughly doubles projected output cost.
* :func:`model_choice_table` — price the *same* nominal usage under several
  models from a (test-injected) price table, proving the model lever.

No new paid runs: every number is derived from synthetic fixtures or the
injected price table. No network, no key, no real run files.
"""

from __future__ import annotations

from agent_debate.core.pricing import ModelPrice, PriceTable
from agent_debate.core.research import (
    RunSummary,
    empirical_points,
    fit_token_model,
    model_choice_table,
    project_grid,
)


def _price_table() -> PriceTable:
    """A small injected price table — cheap vs mid vs dear, distinct rates."""
    return PriceTable(
        version="test",
        models={
            "default": ModelPrice(input_per_1m=3.0, output_per_1m=15.0),
            "cheap": ModelPrice(input_per_1m=1.0, output_per_1m=5.0),
            "mid": ModelPrice(input_per_1m=3.0, output_per_1m=15.0),
            "dear": ModelPrice(input_per_1m=15.0, output_per_1m=75.0),
        },
    )


def _summary(run_id: str, rounds: int, tokens: int, cost: float, lat: float) -> RunSummary:
    """Build a RunSummary carrying the fields the params extractor reads."""
    return RunSummary(
        run_id=run_id,
        rounds=rounds,
        total_tokens=tokens,
        est_cost_usd=cost,
        avg_latency_ms=lat,
    )


def _rows() -> list[RunSummary]:
    """Synthetic rows spanning a range of rounds (mirrors the real spread)."""
    return [
        _summary("a", rounds=3, tokens=60_000, cost=0.18, lat=15_000.0),
        _summary("b", rounds=4, tokens=100_000, cost=0.30, lat=20_000.0),
        _summary("c", rounds=10, tokens=340_000, cost=1.02, lat=28_000.0),
    ]


def test_empirical_points_sorted_by_rounds() -> None:
    """empirical_points returns one point per run, sorted by round count."""
    pts = empirical_points([_rows()[2], _rows()[0], _rows()[1]])
    assert [p.rounds for p in pts] == [3, 4, 10]
    assert pts[0].total_tokens == 60_000
    assert pts[2].est_cost_usd == 1.02


def test_empirical_points_empty() -> None:
    """No rows yields no points (no crash)."""
    assert empirical_points([]) == []


def test_fit_token_model_empty_returns_none() -> None:
    """An empty dataset cannot be fit — returns None instead of dividing by zero."""
    assert fit_token_model([], max_words=150) is None


def test_fit_token_model_recovers_scale() -> None:
    """The fit reproduces the tokens of the point it was derived from."""
    pts = empirical_points(_rows())
    model = fit_token_model(pts, max_words=150)
    assert model is not None
    total = model.total_tokens(rounds=10, max_words=150)
    # Within a sane band of the observed 10-round point it was scaled from.
    assert 0.5 * 340_000 <= total <= 2.0 * 340_000


def test_project_grid_output_cost_scales_with_rounds() -> None:
    """Doubling ROUNDS roughly doubles projected OUTPUT cost (PRD §10, ~linear)."""
    pts = empirical_points(_rows())
    model = fit_token_model(pts, max_words=150)
    assert model is not None
    grid = project_grid(
        model,
        rounds=(5, 10),
        max_words=(150,),
        model_id="mid",
        price_table=_price_table(),
    )
    by_rounds = {c.rounds: c for c in grid}
    ratio = by_rounds[10].output_cost_usd / by_rounds[5].output_cost_usd
    assert 1.8 <= ratio <= 2.2


def test_project_grid_scales_with_max_words() -> None:
    """Doubling MAX_WORDS roughly doubles projected output cost (per-message length)."""
    pts = empirical_points(_rows())
    model = fit_token_model(pts, max_words=150)
    assert model is not None
    grid = project_grid(
        model,
        rounds=(10,),
        max_words=(150, 300),
        model_id="mid",
        price_table=_price_table(),
    )
    by_words = {c.max_words: c for c in grid}
    ratio = by_words[300].output_cost_usd / by_words[150].output_cost_usd
    assert 1.8 <= ratio <= 2.2


def test_project_grid_input_grows_faster_than_output() -> None:
    """Input cost grows super-linearly in rounds (context replay) vs ~linear output."""
    pts = empirical_points(_rows())
    model = fit_token_model(pts, max_words=150)
    assert model is not None
    grid = project_grid(
        model,
        rounds=(5, 10),
        max_words=(150,),
        model_id="mid",
        price_table=_price_table(),
    )
    by_rounds = {c.rounds: c for c in grid}
    in_ratio = by_rounds[10].input_cost_usd / by_rounds[5].input_cost_usd
    out_ratio = by_rounds[10].output_cost_usd / by_rounds[5].output_cost_usd
    assert in_ratio > out_ratio


def test_model_choice_table_prices_same_usage_differently() -> None:
    """Same nominal usage costs more under a dearer model per the price table."""
    rows = model_choice_table(
        input_tokens=1_000_000,
        output_tokens=200_000,
        model_ids=("cheap", "mid", "dear"),
        price_table=_price_table(),
    )
    by_model = {r.model: r for r in rows}
    assert by_model["cheap"].total_cost_usd < by_model["mid"].total_cost_usd
    assert by_model["mid"].total_cost_usd < by_model["dear"].total_cost_usd
    # cheap: 1M*1/1e6 + 0.2M*5/1e6 = 1.0 + 1.0 = 2.0
    assert abs(by_model["cheap"].total_cost_usd - 2.0) < 1e-9


def test_model_choice_table_empty_models() -> None:
    """No model ids yields no rows (no crash)."""
    assert (
        model_choice_table(
            input_tokens=1, output_tokens=1, model_ids=(), price_table=_price_table()
        )
        == []
    )
