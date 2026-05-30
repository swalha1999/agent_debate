"""agent_debate API (``api``) — skeleton (TASKS.md 0.2).

The API surface (PRD §5.1): a FastAPI app exposing run/stream/status endpoints,
a thin shell over the ``core`` SDK. Only the empty package shell exists for
now; later tasks add the real endpoints.

``api`` depends on both ``core`` and ``log`` (PRD §5.1). The re-exports below
import across those workspace edges so the dependencies are exercised, not just
declared (TASKS.md 0.3).
"""

from agent_debate_core import LIBRARY_VERSION as core_version
from agent_debate_log import LIBRARY_VERSION as log_version

__all__ = ["core_version", "log_version"]
