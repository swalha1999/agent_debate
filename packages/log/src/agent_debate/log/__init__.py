"""agent_debate LOG (``agent_debate.log``) — skeleton (TASKS.md 0.2 / 0.3).

The shared logging surface (PRD §5.1): structured logging, cost accounting,
the log schema and sinks. LOG is depended on by every other package. Only the
empty package shell exists for now; later tasks add the real modules.

``LIBRARY_VERSION`` / ``log_version`` are exposed so dependents can re-export
them across the workspace dependency edge, proving the wiring resolves at
runtime (TASKS.md 0.3, issue #3).
"""

from __future__ import annotations

#: Version of the LOG surface; re-exported by dependents to prove the edge.
LIBRARY_VERSION = "1.00"

#: Public alias used by dependents that re-export this package's version.
log_version = LIBRARY_VERSION

__all__ = ["LIBRARY_VERSION", "log_version"]
