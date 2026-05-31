"""Tests for the budget cap + over-budget alert (issue #103, task 15.3, PRD §10).

TDD-first: these assert the 15.3 contract — a configurable budget cap
(``BUDGET_USD`` from config, ``0`` = unlimited), a pure :func:`check_budget`
that reports spent/remaining/over-budget, an :func:`alert_over_budget` that logs
a structured ``system`` event via the LOG package when (and only when) a run
exceeds its cap, and the engine wiring that fires the alert after pricing a
completed run. The price table is injected with deliberately distinctive numbers
so the budget arithmetic is pinned to config, never to hard-coded prices. The
engine path runs offline on a pydantic-ai ``TestModel`` routed through an
injected gatekeeper; no network, no key.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent_debate.core import (
    ApiGatekeeper,
    BudgetStatus,
    DebateConfig,
    DebateSide,
    PriceTable,
    Settings,
    alert_over_budget,
    check_budget,
    load_rate_limit_config,
    setup_debate,
)
from agent_debate.core.engine import run_debate_loop
from pydantic_ai.models.test import TestModel

_TOPIC = "Should remote work be the default for office jobs?"

# A tmp price table with distinctive numbers so the budget arithmetic can only
# match if it reads THESE values (not the repo defaults).
_PRICES = {
    "model_prices": {
        "version": "test",
        "models": {
            "default": {"input_per_1m": 2.0, "output_per_1m": 8.0},
            "anthropic:claude-sonnet-4-6": {"input_per_1m": 1000.0, "output_per_1m": 1000.0},
        },
    }
}


def _price_table() -> PriceTable:
    return PriceTable.model_validate(_PRICES["model_prices"])


def _config(*, rounds: int = 1, budget_usd: float = 0.0) -> DebateConfig:
    return DebateConfig.from_settings(Settings(rounds=rounds, budget_usd=budget_usd))


def test_check_budget_under_cap() -> None:
    """A spend below the cap is not over budget; remaining is the difference."""
    status = check_budget(spent_usd=3.0, budget_usd=10.0)
    assert status.over_budget is False
    assert status.spent_usd == 3.0
    assert status.budget_usd == 10.0
    assert status.remaining_usd == 7.0


def test_check_budget_over_cap() -> None:
    """A spend above the cap is over budget; remaining is clamped to zero."""
    status = check_budget(spent_usd=12.5, budget_usd=10.0)
    assert status.over_budget is True
    assert status.remaining_usd == 0.0


def test_check_budget_zero_cap_is_unlimited() -> None:
    """A ``0`` (or negative) cap means unlimited — never over budget."""
    status = check_budget(spent_usd=999.0, budget_usd=0.0)
    assert status.over_budget is False
    assert status.budget_usd == 0.0


def test_alert_logs_event_when_over_budget(tmp_path: Path) -> None:
    """``alert_over_budget`` writes one structured ``system`` event over the cap."""
    status = check_budget(spent_usd=20.0, budget_usd=10.0)
    fired = alert_over_budget(status, run_id="b1", runs_dir=tmp_path)
    assert fired is True
    line = (tmp_path / "b1.jsonl").read_text(encoding="utf-8").strip()
    record = json.loads(line)
    assert record["event_type"] == "system"
    assert record["payload"]["budget_alert"] is True
    assert record["payload"]["spent_usd"] == 20.0
    assert record["payload"]["budget_usd"] == 10.0


def test_alert_silent_when_under_budget(tmp_path: Path) -> None:
    """No alert event is emitted when the run is within its cap."""
    status = check_budget(spent_usd=2.0, budget_usd=10.0)
    fired = alert_over_budget(status, run_id="b2", runs_dir=tmp_path)
    assert fired is False
    assert not (tmp_path / "b2.jsonl").exists()


def test_budget_status_serialisable() -> None:
    """The status round-trips through JSON (so the API/docs can emit it)."""
    status = BudgetStatus(budget_usd=10.0, spent_usd=4.0, over_budget=False, remaining_usd=6.0)
    restored = BudgetStatus.model_validate_json(status.model_dump_json())
    assert restored == status


def test_engine_fires_alert_when_run_exceeds_cap(tmp_path: Path) -> None:
    """A completed debate over its cap logs the over-budget alert event."""
    config = _config(rounds=1, budget_usd=0.000_001)
    setup = setup_debate(
        topic=_TOPIC,
        config=config,
        models={
            DebateSide.PRO: TestModel(),
            DebateSide.CON: TestModel(),
            "controller": TestModel(),
        },
    )
    gk = ApiGatekeeper(load_rate_limit_config(), run_id="be", runs_dir=tmp_path)
    result = run_debate_loop(
        setup, config, gatekeeper=gk, run_id="be", runs_dir=tmp_path, price_table=_price_table()
    )
    assert result.totals.cost_usd > config.budget_usd
    log_text = (tmp_path / "be.jsonl").read_text(encoding="utf-8")
    assert '"budget_alert": true' in log_text or '"budget_alert":true' in log_text


def test_engine_no_alert_when_unlimited(tmp_path: Path) -> None:
    """The default (``0``) cap is unlimited — a completed run logs no alert."""
    config = _config(rounds=1, budget_usd=0.0)
    setup = setup_debate(
        topic=_TOPIC,
        config=config,
        models={
            DebateSide.PRO: TestModel(),
            DebateSide.CON: TestModel(),
            "controller": TestModel(),
        },
    )
    gk = ApiGatekeeper(load_rate_limit_config(), run_id="bn", runs_dir=tmp_path)
    run_debate_loop(
        setup, config, gatekeeper=gk, run_id="bn", runs_dir=tmp_path, price_table=_price_table()
    )
    log_text = (tmp_path / "bn.jsonl").read_text(encoding="utf-8")
    assert "budget_alert" not in log_text
