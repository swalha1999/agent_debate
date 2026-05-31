"""Check a priced run against its budget cap + alert (task 15.3, PRD §7/§10).

Split out of :mod:`loop.py` (150-line cap) so the loop stays focused on the
debate flow. After :func:`~agent_debate.core.engine._cost.price_result` attaches
the cost-breakdown, this compares the run's grand total against the config-driven
``DebateConfig.budget_usd`` cap and, on an overrun, emits the structured
over-budget **alert** via the LOG package (PRD §10's "configurable budget cap +
over-budget alert"). A ``0`` cap is unlimited, so the default behaviour of every
existing run is unchanged.
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.core.engine.models import DebateConfig
from agent_debate.core.engine.result import DebateResult
from agent_debate.core.pricing import alert_over_budget, check_budget
from agent_debate.log import DEFAULT_RUNS_DIR


def check_run_budget(
    result: DebateResult,
    config: DebateConfig,
    *,
    run_id: str,
    runs_dir: Path | str = DEFAULT_RUNS_DIR,
) -> bool:
    """Compare the priced run against its cap; alert (log) on an overrun.

    Reads the run's grand total from ``result.totals.cost_usd`` (set by
    :func:`~agent_debate.core.engine._cost.price_result`) and the cap from
    ``config.budget_usd`` (config-driven, ``0`` = unlimited). When over budget it
    emits one structured over-budget alert event (LOG package) and returns
    ``True``; otherwise it is a silent no-op returning ``False``.

    Args:
        result: The priced run (``totals.cost_usd`` is the spend).
        config: The run config (``budget_usd`` is the cap).
        run_id: The run id stamped on the alert event.
        runs_dir: Directory holding the per-run JSONL sink.

    Returns:
        ``True`` when an over-budget alert was emitted, ``False`` otherwise.
    """
    status = check_budget(spent_usd=result.totals.cost_usd, budget_usd=config.budget_usd)
    return alert_over_budget(status, run_id=run_id, runs_dir=runs_dir)


__all__ = ["check_run_budget"]
