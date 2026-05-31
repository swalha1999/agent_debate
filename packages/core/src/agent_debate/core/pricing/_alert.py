"""Over-budget alert — log a structured event when a run exceeds its cap (15.3).

Split out of :mod:`agent_debate.core.pricing.budget` so the decision surface stays
pure (no I/O) and this file owns the LOG-package side effect. Given a
:class:`~agent_debate.core.pricing.budget.BudgetStatus`, :func:`alert_over_budget`
emits a single structured ``system`` event (the LOG schema has no dedicated
"alert" kind) carrying the ``budget_alert`` flag plus the spent/cap figures, so an
over-budget run is greppable in ``runs/<run_id>.jsonl`` (PRD §5.8 / §10).

No external API call is made here — only the LOG package's own sink — so the API
gatekeeper (Epic 13) does not apply. Event names/labels are config constants
(:mod:`agent_debate.core.constants`), never inline literals (guideline §7.2).
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.core import constants
from agent_debate.core.pricing.budget import BudgetStatus
from agent_debate.log import DEFAULT_RUNS_DIR, log_event


def alert_over_budget(
    status: BudgetStatus,
    *,
    run_id: str,
    runs_dir: Path | str = DEFAULT_RUNS_DIR,
) -> bool:
    """Emit the over-budget alert event when ``status`` is over budget.

    A no-op (returns ``False``, logs nothing) when the run is within its cap or
    the cap is unlimited, so the alert fires *only* on a genuine overrun. When
    over budget it logs one structured ``system`` event — ``payload`` carries the
    ``budget_alert`` flag and the spent / cap / remaining figures — and returns
    ``True``.

    Args:
        status: The budget comparison (from :func:`check_budget`).
        run_id: The run id stamped on the emitted alert event.
        runs_dir: Directory holding the per-run JSONL sink.

    Returns:
        ``True`` when an alert was emitted, ``False`` otherwise.
    """
    if not status.over_budget:
        return False
    log_event(
        run_id=run_id,
        agent=constants.BUDGET_ALERT_LOG_AGENT,
        event_type=constants.BUDGET_ALERT_EVENT_TYPE,
        round=constants.BUDGET_ALERT_ROUND,
        payload={
            constants.BUDGET_ALERT_TAG: True,
            "spent_usd": status.spent_usd,
            "budget_usd": status.budget_usd,
            "remaining_usd": status.remaining_usd,
        },
        runs_dir=runs_dir,
    )
    return True


__all__ = ["alert_over_budget"]
