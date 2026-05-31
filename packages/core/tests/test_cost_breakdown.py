"""Tests for the cost-breakdown table (issue #102, task 15.2, PRD §10/§11).

TDD-first: these assert the 15.2 contract — per-model + overall cost
(input/output tokens × the *file* price table → USD), the engine populating
:attr:`DebateResult.totals` ``cost_usd`` + the per-model breakdown on a completed
run, a markdown ``format_cost_table`` renderer, and an ``aggregate_costs`` helper
that sums multiple runs. Prices come from a tmp price table (custom numbers →
expected cost) so the assertions pin the arithmetic to config, never to hard-coded
prices. The engine path runs offline on a pydantic-ai ``TestModel`` (deterministic
non-zero usage) routed through an injected gatekeeper; no network, no key.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent_debate.core import (
    ApiGatekeeper,
    CostBreakdown,
    DebateConfig,
    DebateMessage,
    DebateResult,
    DebateSide,
    ModelCostRow,
    PriceTable,
    Settings,
    aggregate_costs,
    cost_breakdown_from_result,
    format_cost_table,
    load_rate_limit_config,
    setup_debate,
)
from agent_debate.core.engine import run_debate_loop
from pydantic_ai.models.test import TestModel

_TOPIC = "Should remote work be the default for office jobs?"

# A tmp price table with deliberately distinctive numbers so a priced cost can
# only match if it reads THESE values (not the repo defaults).
_PRICES = {
    "model_prices": {
        "version": "test",
        "models": {
            "default": {"input_per_1m": 2.0, "output_per_1m": 8.0},
            "pro:model": {"input_per_1m": 10.0, "output_per_1m": 100.0},
            "con:model": {"input_per_1m": 5.0, "output_per_1m": 50.0},
        },
    }
}


def _price_table() -> PriceTable:
    return PriceTable.model_validate(_PRICES["model_prices"])


def _msg(side: DebateSide, *, inp: int, out: int = 0) -> DebateMessage:
    return DebateMessage(round=1, side=side, content="x", input_tokens=inp, output_tokens=out)


def _result_with(messages: list[DebateMessage]) -> DebateResult:
    return DebateResult(topic=_TOPIC, transcript=messages)


def _config(*, rounds: int = 1, max_words: int = 40) -> DebateConfig:
    return DebateConfig.from_settings(Settings(rounds=rounds, max_words=max_words))


def test_per_model_and_overall_cost_from_file_table() -> None:
    """Per-model rows + overall total derive tokens × the *table* prices."""
    messages = [
        _msg(DebateSide.PRO, inp=1_000_000, out=1_000_000),
        _msg(DebateSide.CON, inp=2_000_000),
    ]
    side_models = {DebateSide.PRO: "pro:model", DebateSide.CON: "con:model"}
    breakdown = cost_breakdown_from_result(
        _result_with(messages), side_models=side_models, price_table=_price_table()
    )
    rows = {r.model: r for r in breakdown.rows}
    # Pro: 1M in × $10 + 1M out × $100 = 110.
    assert rows["pro:model"].input_cost == 10.0
    assert rows["pro:model"].output_cost == 100.0
    assert rows["pro:model"].total_cost == 110.0
    # Con: 2M in × $5 + 0 out = 10.
    assert rows["con:model"].input_cost == 10.0
    assert rows["con:model"].total_cost == 10.0
    # Overall = 120.
    assert breakdown.total_cost == 120.0
    assert breakdown.input_tokens == 3_000_000
    assert breakdown.output_tokens == 1_000_000


def test_shared_model_rows_are_merged() -> None:
    """Two sides on the same model collapse into one per-model row."""
    messages = [
        _msg(DebateSide.PRO, inp=1_000_000),
        _msg(DebateSide.CON, inp=1_000_000),
    ]
    side_models = {DebateSide.PRO: "shared", DebateSide.CON: "shared"}
    breakdown = cost_breakdown_from_result(
        _result_with(messages), side_models=side_models, price_table=_price_table()
    )
    assert len(breakdown.rows) == 1
    # Unknown model "shared" → default ($2 in). 2M in × $2 = 4.
    assert breakdown.rows[0].input_tokens == 2_000_000
    assert breakdown.total_cost == 4.0


def test_format_cost_table_renders_markdown(tmp_path: Path) -> None:
    """The formatter emits a markdown table with a per-model row + overall row."""
    messages = [_msg(DebateSide.PRO, inp=1_000_000, out=1_000_000)]
    side_models = {DebateSide.PRO: "pro:model", DebateSide.CON: "con:model"}
    breakdown = cost_breakdown_from_result(
        _result_with(messages), side_models=side_models, price_table=_price_table()
    )
    table = format_cost_table(breakdown)
    assert table.startswith("|")
    lines = table.splitlines()
    # Header + separator + one model row + overall row = 4 lines.
    assert len(lines) == 4
    assert "pro:model" in table
    assert "Overall" in table or "overall" in table
    assert "110" in table  # the pro total cost appears.


def test_aggregate_costs_sums_breakdowns() -> None:
    """``aggregate_costs`` sums multiple runs' per-model rows + overall total."""
    side_models = {DebateSide.PRO: "pro:model", DebateSide.CON: "con:model"}
    msgs_a = [_msg(DebateSide.PRO, inp=1_000_000)]
    msgs_b = [_msg(DebateSide.PRO, inp=1_000_000)]
    b_a = cost_breakdown_from_result(
        _result_with(msgs_a), side_models=side_models, price_table=_price_table()
    )
    b_b = cost_breakdown_from_result(
        _result_with(msgs_b), side_models=side_models, price_table=_price_table()
    )
    agg = aggregate_costs([b_a, b_b])
    assert agg.input_tokens == 2_000_000
    # 2 × (1M × $10) = 20.
    assert agg.total_cost == 20.0
    assert len(agg.rows) == 1


def test_engine_populates_cost_on_completed_debate(tmp_path: Path) -> None:
    """A completed debate has a non-zero priced ``cost_usd`` + per-model breakdown."""
    setup = setup_debate(
        topic=_TOPIC,
        config=_config(rounds=1),
        models={
            DebateSide.PRO: TestModel(),
            DebateSide.CON: TestModel(),
            "controller": TestModel(),
        },
    )
    gk = ApiGatekeeper(load_rate_limit_config(), run_id="c1", runs_dir=tmp_path)
    result = run_debate_loop(
        setup,
        _config(rounds=1),
        gatekeeper=gk,
        run_id="c1",
        runs_dir=tmp_path,
        price_table=_price_table(),
    )
    assert result.totals.cost_usd > 0.0
    assert result.cost_breakdown is not None
    assert result.cost_breakdown.total_cost == result.totals.cost_usd
    assert result.cost_breakdown.rows


def test_breakdown_is_serialisable() -> None:
    """The breakdown round-trips through JSON (so the API/docs can emit it)."""
    row = ModelCostRow(
        model="m", input_tokens=1, output_tokens=2, input_cost=0.1, output_cost=0.2, total_cost=0.3
    )
    breakdown = CostBreakdown(rows=[row], input_tokens=1, output_tokens=2, total_cost=0.3)
    restored = CostBreakdown.model_validate_json(breakdown.model_dump_json())
    assert restored == breakdown
    assert json.loads(breakdown.model_dump_json())["total_cost"] == 0.3
