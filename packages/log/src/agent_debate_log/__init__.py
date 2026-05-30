"""agent_debate LOG (``log``) — skeleton (TASKS.md 0.2).

The shared logging surface (PRD §5.1): structured logging, cost accounting,
the log schema and sinks. LOG is depended on by every other package. Only the
empty package shell exists for now; later tasks add the real modules.
"""

#: Package version surface, also used to prove cross-package imports resolve
#: (TASKS.md 0.3). Kept in sync with ``pyproject.toml`` ``[project].version``.
LIBRARY_VERSION = "1.00"

__all__ = ["LIBRARY_VERSION"]
