"""agent_debate SDK (``core``) — skeleton (TASKS.md 0.2).

This is the heart of the system (PRD §5.1): the debate engine, agents, skills,
controller, API gatekeeper and search plug-ins. Only the empty package shell
exists for now; later tasks add the real modules.

``core`` depends on the shared ``log`` package (PRD §5.1). The re-export below
imports across that workspace edge so the dependency is exercised, not just
declared (TASKS.md 0.3).
"""

from agent_debate_log import LIBRARY_VERSION as log_version

#: Package version surface, also used to prove cross-package imports resolve
#: (TASKS.md 0.3). Kept in sync with ``pyproject.toml`` ``[project].version``.
LIBRARY_VERSION = "1.00"

__all__ = ["LIBRARY_VERSION", "log_version"]
