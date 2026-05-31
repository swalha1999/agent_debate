"""Price a completed run's cost-breakdown into its result (task 15.2, PRD §10/§11).

Split out of :mod:`loop.py` (150-line cap) so the loop stays focused on the
debate flow. Given the finished :class:`~agent_debate.core.engine.result.
DebateResult` and the run :class:`~agent_debate.core.engine.models.DebateConfig`,
this maps each side to its configured model, prices the captured tokens against
the (config-driven, or injected) price table, and returns a copy carrying the
per-model :class:`~agent_debate.core.pricing.breakdown.CostBreakdown` plus the
overall ``totals.cost_usd``.
"""

from __future__ import annotations

from agent_debate.core.engine.models import DebateConfig
from agent_debate.core.engine.result import DebateResult
from agent_debate.core.pricing import (
    PriceTable,
    cost_breakdown_from_result,
    load_price_table,
)
from agent_debate.core.skills import DebateSide


def price_result(
    result: DebateResult,
    config: DebateConfig,
    price_table: PriceTable | None,
) -> DebateResult:
    """Attach the per-model cost-breakdown + repriced ``cost_usd`` (PRD §10/§11).

    Each side's tokens are priced against its configured model via the (config-
    driven, or injected) price table; the overall total becomes ``totals.cost_usd``
    and the per-model table is stored on :attr:`DebateResult.cost_breakdown`.

    Args:
        result: The completed run (transcript + closing turns carry the tokens).
        config: The run config (``pro_model`` / ``con_model`` map sides to models).
        price_table: A pre-loaded price table; when ``None`` the repo-root
            ``config/model_prices.json`` is loaded (no hard-coded prices).
    """
    table = price_table if price_table is not None else load_price_table()
    breakdown = cost_breakdown_from_result(
        result,
        side_models={DebateSide.PRO: config.pro_model, DebateSide.CON: config.con_model},
        price_table=table,
    )
    return result.model_copy(
        update={
            "cost_breakdown": breakdown,
            "totals": result.totals.model_copy(update={"cost_usd": breakdown.total_cost}),
        }
    )


__all__ = ["price_result"]
