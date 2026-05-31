"""Config-driven host/port resolution for the API server (task 10.1, #68).

No hard-coded values scattered through the code: the Uvicorn bind address comes
from the ``API_HOST`` / ``API_PORT`` environment variables, each falling back to
a single named constant. Keeping this in one tiny module gives both the app and
the entrypoint one source of truth (guideline §7.2).
"""

from __future__ import annotations

import os

#: Default bind host — localhost-only, the safe default for a dev surface.
DEFAULT_API_HOST = "127.0.0.1"

#: Default bind port for the API server.
DEFAULT_API_PORT = 8000

#: Env var names (single source of truth, never inline string literals).
HOST_ENV_VAR = "API_HOST"
PORT_ENV_VAR = "API_PORT"


def resolve_host() -> str:
    """Return the bind host from ``API_HOST`` or the named default."""
    return os.environ.get(HOST_ENV_VAR, DEFAULT_API_HOST)


def resolve_port() -> int:
    """Return the bind port from ``API_PORT`` or the named default."""
    raw = os.environ.get(PORT_ENV_VAR)
    if raw is None or not raw.strip():
        return DEFAULT_API_PORT
    return int(raw)
