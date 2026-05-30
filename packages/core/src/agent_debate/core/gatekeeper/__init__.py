"""API gatekeeper subpackage — the chokepoint for external calls (Epic 13).

``docs/prds/api-gatekeeper.md``: a single manager that every external LLM/search
call passes through, enforcing config-driven rate limits, queueing overflow,
retrying transient failures and logging everything.

Task 13.1 ships only the *config* surface (models + loader); subsequent tasks
add ``ApiGatekeeper.execute`` (13.2), the FIFO overflow queue (13.3), retry +
concurrency control (13.4) and ``get_queue_status`` (13.5). This package gives
that growth a clean home; the config re-exports below are its first members.
"""

from __future__ import annotations

from agent_debate.core.gatekeeper.config import (
    DEFAULT_SERVICE,
    RATE_LIMITS_FILENAME,
    RateLimitConfig,
    ServiceLimits,
    load_rate_limit_config,
)

__all__ = [
    "DEFAULT_SERVICE",
    "RATE_LIMITS_FILENAME",
    "RateLimitConfig",
    "ServiceLimits",
    "load_rate_limit_config",
]
