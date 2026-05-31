"""Tests for token / cost accounting (issue #52, task 6.7, PRD §5.8 + §10).

TDD-first: these assert the 6.7 contract before the usage-capture + aggregation
code exists. They cover:

* **Per-call capture** — a single debater turn reads token usage off the model
  result and stamps it on the returned :class:`DebateMessage` *and* the emitted
  ``message`` :class:`LogEvent`'s ``tokens`` field (feeds the LOG package).
* **Aggregation** — :class:`CostTotals` (via ``from_messages``) sums grand totals
  and a structured **per-agent** + **per-round** breakdown.
* **Whole-debate totals equal the sum of the turns**, including the closing phase.
* **Serialisability** — the breakdown round-trips so Epic 15 can price it later.

Everything runs offline on a pydantic-ai ``TestModel`` (deterministic, non-zero
usage: it reports ``input_tokens``/``output_tokens`` per call) routed through an
injected :class:`ApiGatekeeper`; no network, no key. Prices are **not** asserted
— cost is Epic 15's price-table job; 6.7 only captures + aggregates *tokens*.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_debate.core import (
    ApiGatekeeper,
    CostTotals,
    DebateConfig,
    DebateMessage,
    DebateSide,
    Settings,
    UsageBreakdown,
    load_rate_limit_config,
    setup_debate,
)
from agent_debate.core.engine import run_debate_loop
from pydantic_ai.models import Model
from pydantic_ai.models.test import TestModel

_TOPIC = "Should remote work be the default for office jobs?"


def _config(*, rounds: int = 2, max_words: int = 50) -> DebateConfig:
    return DebateConfig.from_settings(Settings(rounds=rounds, max_words=max_words))


def _models(*, pro: Model, con: Model) -> dict[object, Model]:
    return {DebateSide.PRO: pro, DebateSide.CON: con, "controller": TestModel()}


def _gatekeeper(run_id: str, runs_dir: Path) -> ApiGatekeeper:
    return ApiGatekeeper(load_rate_limit_config(), run_id=run_id, runs_dir=runs_dir)


def _events(runs_dir: Path, run_id: str) -> list[dict[str, Any]]:
    path = runs_dir / f"{run_id}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


def _run(tmp_path: Path, run_id: str, *, rounds: int = 2):  # type: ignore[no-untyped-def]
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=rounds)
    setup = setup_debate(_TOPIC, config, models=_models(pro=TestModel(), con=TestModel()))
    result = run_debate_loop(
        setup, config, gatekeeper=_gatekeeper(run_id, runs_dir), run_id=run_id, runs_dir=runs_dir
    )
    return result, runs_dir


def test_turn_captures_usage_onto_message_and_event(tmp_path: Path) -> None:
    """Each turn stamps real (non-zero) token usage on its message + ``message`` event."""
    result, runs_dir = _run(tmp_path, "t1", rounds=1)
    pro = next(m for m in result.transcript if m.side is DebateSide.PRO)
    # TestModel reports deterministic, non-zero usage per call.
    assert pro.input_tokens > 0
    assert pro.output_tokens > 0
    message_events = [
        e for e in _events(runs_dir, "t1") if e["event_type"] == "message" and e["round"] >= 1
    ]
    assert message_events, "expected at least one numbered message event"
    for event in message_events:
        assert event["tokens"] is not None
        assert event["tokens"] > 0


def test_cost_totals_breakdown_by_agent_and_round() -> None:
    """``from_messages`` builds grand totals + per-agent + per-round breakdowns."""
    messages = [
        DebateMessage(round=1, side=DebateSide.PRO, content="p1", input_tokens=10, output_tokens=2),
        DebateMessage(round=1, side=DebateSide.CON, content="c1", input_tokens=20, output_tokens=3),
        DebateMessage(round=2, side=DebateSide.PRO, content="p2", input_tokens=30, output_tokens=4),
    ]
    totals = CostTotals.from_messages(messages)
    assert totals.input_tokens == 60
    assert totals.output_tokens == 9
    assert totals.total_tokens == 69
    # Per agent.
    assert totals.by_agent["pro"] == UsageBreakdown(
        input_tokens=40, output_tokens=6, total_tokens=46
    )
    assert totals.by_agent["con"] == UsageBreakdown(
        input_tokens=20, output_tokens=3, total_tokens=23
    )
    # Per round.
    assert totals.by_round[1].total_tokens == 35
    assert totals.by_round[2].total_tokens == 34
    # Cost is left to Epic 15 (no price table here).
    assert totals.cost_usd == 0.0


def test_breakdowns_sum_to_grand_totals() -> None:
    """The per-agent and per-round breakdowns each re-sum to the grand totals."""
    messages = [
        DebateMessage(round=r, side=s, content="x", input_tokens=r * 5, output_tokens=r)
        for r in (1, 2, 3)
        for s in (DebateSide.PRO, DebateSide.CON)
    ]
    totals = CostTotals.from_messages(messages)
    by_agent_total = sum(b.total_tokens for b in totals.by_agent.values())
    by_round_total = sum(b.total_tokens for b in totals.by_round.values())
    assert by_agent_total == totals.total_tokens
    assert by_round_total == totals.total_tokens


def test_multi_round_debate_totals_equal_sum_of_turns(tmp_path: Path) -> None:
    """A whole debate's totals equal the sum of every turn (transcript + closing)."""
    result, _ = _run(tmp_path, "t2", rounds=2)
    turns = result.transcript + result.closing_discussion
    assert result.totals.total_tokens == sum(m.input_tokens + m.output_tokens for m in turns)
    assert result.totals.total_tokens > 0
    # The closing turns also carry captured usage.
    assert all(m.input_tokens + m.output_tokens > 0 for m in result.closing_discussion)
    # Per-agent breakdown re-sums to the grand total over the whole run.
    by_agent_total = sum(b.total_tokens for b in result.totals.by_agent.values())
    assert by_agent_total == result.totals.total_tokens


def test_usage_breakdown_is_serialisable(tmp_path: Path) -> None:
    """Totals + breakdowns round-trip through JSON so Epic 15 can price them."""
    result, _ = _run(tmp_path, "t3", rounds=1)
    dumped = result.totals.model_dump_json()
    restored = CostTotals.model_validate_json(dumped)
    assert restored == result.totals
    assert restored.by_agent["pro"].total_tokens > 0
