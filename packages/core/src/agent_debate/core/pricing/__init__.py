"""Per-model pricing subpackage — token counts → USD cost (Epic 15, issue #101).

PRD §10 (Costs & pricing): a debate's token totals are converted to a cost via a
config-driven per-model price table (input/output USD per 1M tokens). Task 15.1
ships that *price* surface — the versioned ``config/model_prices.json`` data
file, typed models + loader (:mod:`~agent_debate.core.pricing.config`) and the
:func:`compute_cost` primitive (:mod:`~agent_debate.core.pricing._cost`). Wiring
it into :class:`DebateResult.cost_usd` / per-agent cost is task 15.2.

"0 hard-coded prices": prices live solely in ``config/model_prices.json``; the
only Python constants are the file name, the ``default`` key and the per-1M
divisor. The re-exports below are this package's public surface.
"""

from __future__ import annotations

from agent_debate.core.pricing._cost import TOKENS_PER_PRICE_UNIT, compute_cost
from agent_debate.core.pricing._format import format_cost_table
from agent_debate.core.pricing.breakdown import (
    CostBreakdown,
    ModelCostRow,
    aggregate_costs,
    cost_breakdown_from_result,
)
from agent_debate.core.pricing.config import (
    DEFAULT_MODEL,
    MODEL_PRICES_FILENAME,
    ModelPrice,
    PriceTable,
    get_model_price,
    load_price_table,
)

__all__ = [
    "DEFAULT_MODEL",
    "MODEL_PRICES_FILENAME",
    "TOKENS_PER_PRICE_UNIT",
    "CostBreakdown",
    "ModelCostRow",
    "ModelPrice",
    "PriceTable",
    "aggregate_costs",
    "compute_cost",
    "cost_breakdown_from_result",
    "format_cost_table",
    "get_model_price",
    "load_price_table",
]
