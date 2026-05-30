"""agent_debate UI (``agent_debate.ui``) — skeleton (TASKS.md 0.2 / 0.3).

The UI surface (PRD §5.1): a web frontend that consumes the ``api`` surface to
show a live transcript and the final verdict. Only the empty package shell
exists for now; later tasks add the real frontend.

``ui`` depends on both ``core`` and ``log`` (issue #3): it re-exports their
versions by importing across the edges, proving the dependencies resolve at
runtime.
"""

from __future__ import annotations

from agent_debate.core import core_version
from agent_debate.log import log_version

#: Version of the UI surface.
LIBRARY_VERSION = "1.00"

__all__ = ["LIBRARY_VERSION", "core_version", "log_version"]
