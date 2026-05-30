"""API gatekeeper subpackage — the chokepoint for external calls (Epic 13).

``docs/prds/api-gatekeeper.md``: a single manager that every external LLM/search
call passes through, enforcing config-driven rate limits, queueing overflow,
retrying transient failures and logging everything.

Task 13.1 shipped the *config* surface (models + loader); task 13.2 adds the
core :class:`ApiGatekeeper` with :meth:`~ApiGatekeeper.execute` (check → run →
log). Subsequent tasks add the FIFO overflow queue (13.3), retry + concurrency
control (13.4) and the full ``get_queue_status`` (13.5). This package gives that
growth a clean home; the re-exports below are its public surface.
"""

from __future__ import annotations

from agent_debate.core.gatekeeper._gatekeeper import ApiGatekeeper
from agent_debate.core.gatekeeper.config import (
    DEFAULT_SERVICE,
    RATE_LIMITS_FILENAME,
    RateLimitConfig,
    ServiceLimits,
    load_rate_limit_config,
)
from agent_debate.core.gatekeeper.errors import QueueFullError, RateLimitExceededError
from agent_debate.core.gatekeeper.types import QueueStatus

__all__ = [
    "DEFAULT_SERVICE",
    "RATE_LIMITS_FILENAME",
    "ApiGatekeeper",
    "QueueFullError",
    "QueueStatus",
    "RateLimitConfig",
    "RateLimitExceededError",
    "ServiceLimits",
    "load_rate_limit_config",
]
