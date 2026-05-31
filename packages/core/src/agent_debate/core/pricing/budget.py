"""Budget cap + over-budget alert (task 15.3, issue #103, PRD §7/§10).

Epic 15 makes cost *actionable*: a run's priced total (task 15.2's
:class:`~agent_debate.core.pricing.breakdown.CostBreakdown`) is checked against a
**configurable budget cap** (``BUDGET_USD``), and an over-budget run raises a
structured **alert**. This module is the pure decision surface — the typed,
JSON-serialisable :class:`BudgetStatus` value and the :func:`check_budget`
comparator. The LOG-emitting :func:`alert_over_budget` lives next door in
:mod:`agent_debate.core.pricing._alert` (split to hold the 150-line cap).

"0 hard-coded values": the cap is read from config (``BUDGET_USD`` →
:class:`~agent_debate.core.engine.models.DebateConfig.budget_usd`); the only
literal here is the documented "``<= 0`` means unlimited" sentinel.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BudgetStatus(BaseModel):
    """The outcome of comparing a run's spend against its budget cap (PRD §10).

    Attributes:
        budget_usd: The configured USD cap; ``<= 0`` means unlimited (no cap).
        spent_usd: The run's priced total cost (from the cost-breakdown total).
        over_budget: ``True`` when a positive cap was set and ``spent`` exceeds it.
        remaining_usd: Headroom left under the cap (``0.0`` once over budget, and
            ``0.0`` for an unlimited cap — there is no finite remaining figure).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    budget_usd: float = Field(ge=0.0)
    spent_usd: float = Field(ge=0.0)
    over_budget: bool
    remaining_usd: float = Field(ge=0.0)


def check_budget(*, spent_usd: float, budget_usd: float) -> BudgetStatus:
    """Compare ``spent_usd`` against ``budget_usd`` into a :class:`BudgetStatus`.

    A cap ``<= 0`` is treated as **unlimited**: the run is never over budget and
    ``remaining_usd`` is ``0.0`` (there is no finite headroom to report). For a
    positive cap, ``over_budget`` is set when the spend strictly exceeds it and
    ``remaining_usd`` is the non-negative headroom (clamped at zero once over).

    Args:
        spent_usd: The run's priced total cost (cost-breakdown grand total).
        budget_usd: The configured USD cap (``<= 0`` = unlimited).

    Returns:
        A :class:`BudgetStatus` describing the comparison.
    """
    unlimited = budget_usd <= 0.0
    over_budget = (not unlimited) and spent_usd > budget_usd
    remaining = 0.0 if unlimited else max(budget_usd - spent_usd, 0.0)
    return BudgetStatus(
        budget_usd=max(budget_usd, 0.0),
        spent_usd=spent_usd,
        over_budget=over_budget,
        remaining_usd=remaining,
    )


__all__ = ["BudgetStatus", "check_budget"]
