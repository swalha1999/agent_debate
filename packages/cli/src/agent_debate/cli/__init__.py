"""agent_debate CLI (``agent_debate.cli``) — skeleton (TASKS.md 0.2 / 0.3).

The CLI surface (PRD §5.1, §6): a Typer app to launch and watch a debate from the
terminal, a thin shell over the ``core`` SDK. The ``run`` command (task 9.1)
lives in :mod:`agent_debate.cli.app`.

``cli`` depends on both ``core`` and ``log`` (issue #3): it re-exports their
versions by importing across the edges, proving the dependencies resolve at
runtime.

The Typer app is re-exported as :data:`cli_app` (NOT ``app`` — that name would
shadow the :mod:`agent_debate.cli.app` submodule the entry point/tests import).
"""

from __future__ import annotations

from agent_debate.cli.app import app as cli_app
from agent_debate.core import core_version
from agent_debate.log import log_version

#: Version of the CLI surface.
LIBRARY_VERSION = "1.00"

__all__ = ["LIBRARY_VERSION", "cli_app", "core_version", "log_version"]
