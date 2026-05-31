"""agent_debate UI (``agent_debate.ui``) — web frontend over the API (PRD §6).

The UI surface (PRD §5.1): a web frontend that consumes the ``api`` surface. The
topic-input page (task 11.1) lets a user start a debate; the live transcript +
verdict views land in later 11.x tasks.

:func:`create_app` is the FastAPI app factory (mirroring the API's) that serves
the static frontend with a config-driven API base URL injected. ``ui`` also
depends on ``core`` and ``log`` (issue #3) and re-exports their versions,
proving the dependency edges resolve at runtime.
"""

from __future__ import annotations

from agent_debate.core import core_version
from agent_debate.log import log_version
from agent_debate.ui.app import create_app

#: Version of the UI surface.
LIBRARY_VERSION = "1.00"

__all__ = ["LIBRARY_VERSION", "core_version", "create_app", "log_version"]
