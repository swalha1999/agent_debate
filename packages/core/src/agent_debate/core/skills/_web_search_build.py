"""Provider assembly for the ``web_search`` skill (task 4.1, issue #32).

Splits the *construction* of the search provider stack out of
:mod:`agent_debate.core.skills.web_search` so that module stays a thin policy
flow (validate → search → sanitise → log) under the 150-line limit.

The stack composes the two independent decorators the search Epic already ships:

1. :func:`create_search_provider` wraps the active backend (whatever
   ``SEARCH_BACKEND`` selects — provider-agnostic) in a
   :class:`~agent_debate.core.search.GatekeptSearchProvider` so its live external
   call routes **through** the API gatekeeper (Epic 13, rate-limited).
2. :class:`~agent_debate.core.search.ResilientSearchProvider` then wraps *that* so
   a flaky / failed search degrades to ``[]`` instead of crashing the debate
   (sub-PRD §6) — never raising to the model.

No values are hard-coded: the resilience retry knobs come from the ``search``
:class:`ServiceLimits` in ``config/rate_limits.json`` and the per-call timeout
from :pyattr:`Settings.turn_timeout_s`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from agent_debate.core.constants import SEARCH_SERVICE
from agent_debate.core.gatekeeper import load_rate_limit_config
from agent_debate.core.search import (
    ResilientSearchProvider,
    create_search_provider,
)

if TYPE_CHECKING:
    from agent_debate.core.engine.gatekeeper_proto import Gatekeeper
    from agent_debate.core.settings import Settings


def build_search_provider(
    settings: Settings,
    *,
    gatekeeper: Gatekeeper | None,
    run_id: str,
    runs_dir: Path | str,
) -> ResilientSearchProvider:
    """Assemble the gatekeeper-routed, resilience-wrapped active search provider.

    The active backend (``settings.search_backend``) is wrapped by
    :func:`create_search_provider` so its external call routes through the API
    gatekeeper, then by :class:`ResilientSearchProvider` so a failure returns
    ``[]``. Retry limits come from the ``search`` service config and the timeout
    from ``settings.turn_timeout_s`` — nothing is hard-coded.

    Args:
        settings: Runtime settings selecting the backend + per-turn timeout.
        gatekeeper: The API gatekeeper to route the provider's call through.
        run_id: Run id the resilience wrapper logs degradation under.
        runs_dir: Directory holding the per-run JSONL sink.

    Returns:
        The composed :class:`ResilientSearchProvider` ready to ``search``.
    """
    gatekept = create_search_provider(settings, gatekeeper=gatekeeper)
    limits = load_rate_limit_config().get_service_limits(SEARCH_SERVICE)
    return ResilientSearchProvider(
        gatekept,
        limits=limits,
        timeout_s=float(settings.turn_timeout_s),
        run_id=run_id,
        runs_dir=runs_dir,
    )


__all__ = ["build_search_provider"]
