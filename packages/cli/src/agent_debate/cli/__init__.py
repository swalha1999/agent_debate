"""agent_debate CLI (``agent_debate.cli``) — skeleton (TASKS.md 0.2 / 0.3).

The CLI surface (PRD §5.1): a Typer app to launch and watch a debate from the
terminal, a thin shell over the ``core`` SDK. Only the empty package shell
exists for now; later tasks add the real commands.

``cli`` depends on both ``core`` and ``log`` (issue #3): it re-exports their
versions by importing across the edges, proving the dependencies resolve at
runtime.
"""

from __future__ import annotations

from agent_debate.core import core_version
from agent_debate.log import log_version

#: Version of the CLI surface.
LIBRARY_VERSION = "1.00"

__all__ = ["LIBRARY_VERSION", "core_version", "log_version"]
