"""Token-count → USD cost arithmetic (task 15.1, issue #101).

Given a model id, an input-token count and an output-token count, price the call
from the per-model price table (:mod:`agent_debate.core.pricing.config`). Prices
are quoted per 1,000,000 tokens, so the only literal here is that divisor — a
single named constant, not a price (prices live solely in the config file).

Wiring this into :class:`DebateResult.cost_usd` / per-agent cost is task 15.2;
this function is the ready-to-use primitive that task builds on.
"""

from __future__ import annotations

from agent_debate.core.pricing.config import PriceTable, get_model_price

#: Tokens per pricing unit: prices in the config file are quoted per this many
#: tokens (USD per 1M tokens). A named unit, not a price value (guideline §7.2).
TOKENS_PER_PRICE_UNIT = 1_000_000


def compute_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    price_table: PriceTable | None = None,
) -> float:
    """Return the USD cost of a call from the per-model price table.

    Cost = ``input_tokens / 1e6 * input_per_1m + output_tokens / 1e6 *
    output_per_1m``, with both per-1M prices read from the table (unknown models
    fall back to its ``default`` entry).

    :param model: the ``provider:model`` (or bare model) id being priced.
    :param input_tokens: prompt tokens consumed (``>= 0``).
    :param output_tokens: completion tokens produced (``>= 0``).
    :param price_table: a pre-loaded :class:`PriceTable`; when ``None`` the
        repo-root ``config/model_prices.json`` is loaded.
    """
    price = get_model_price(model, price_table)
    input_cost = input_tokens / TOKENS_PER_PRICE_UNIT * price.input_per_1m
    output_cost = output_tokens / TOKENS_PER_PRICE_UNIT * price.output_per_1m
    return input_cost + output_cost


__all__ = ["TOKENS_PER_PRICE_UNIT", "compute_cost"]
