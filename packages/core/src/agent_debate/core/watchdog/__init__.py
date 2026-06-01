"""Keep-alive Watchdog subpackage (issue #216, HW2 §8.6).

HW2 §8.6 — *Watchdog with keep-alive*: a fallen (hung/dead/stopped-beating)
worker must be detected via a keep-alive heartbeat and restarted, IN ADDITION to
the per-turn timeout + retry seam (:mod:`agent_debate.core.engine._call`, which
guards a single model call). This subpackage is the reusable, provider-agnostic
SDK component for that liveness concern:

* :class:`WatchdogConfig` / :func:`load_watchdog_config` — the config surface
  (``config/watchdog.json``), mirroring the rate-limit config: every interval/
  timeout/restart value is read from the file, none hard-coded.
* :class:`Watchdog` / :class:`WatchdogResult` — the supervisor: monitor a
  worker's heartbeat, kill + restart it when it falls (up to ``max_restarts``),
  logging each action via the LOG package. The clock/sleep/worker callables are
  injected so it is deterministic and testable.
"""

from __future__ import annotations

from agent_debate.core.watchdog._config import (
    WATCHDOG_FILENAME,
    WatchdogConfig,
    load_watchdog_config,
)
from agent_debate.core.watchdog._watchdog import Watchdog, WatchdogResult

__all__ = [
    "WATCHDOG_FILENAME",
    "Watchdog",
    "WatchdogConfig",
    "WatchdogResult",
    "load_watchdog_config",
]
