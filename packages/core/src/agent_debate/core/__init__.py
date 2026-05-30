"""agent_debate SDK (``agent_debate.core``) — skeleton (TASKS.md 0.2 / 0.3).

This is the heart of the system (PRD §5.1): the debate engine, agents, skills,
controller, API gatekeeper and search plug-ins. Only the empty package shell
exists for now; later tasks add the real modules.

``core`` depends on ``log`` (issue #3): it re-exports ``log_version`` by
importing across the edge, proving the dependency resolves at runtime.
"""

from __future__ import annotations

from agent_debate.log import log_version

#: Version of the core SDK surface.
LIBRARY_VERSION = "1.00"

#: Public alias used by dependents that re-export this package's version.
core_version = LIBRARY_VERSION

__all__ = ["LIBRARY_VERSION", "core_version", "log_version"]
