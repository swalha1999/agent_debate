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

#: Default browser origin the UI dev server runs on (Vite's default port).
#: Safe local-dev default; production sets ``CORS_ORIGINS`` explicitly.
DEFAULT_UI_ORIGIN = "http://localhost:5173"

#: Env var names (single source of truth, never inline string literals).
HOST_ENV_VAR = "API_HOST"
PORT_ENV_VAR = "API_PORT"

#: Comma-separated list of browser origins allowed by CORS (overrides default).
CORS_ORIGINS_ENV_VAR = "CORS_ORIGINS"


def resolve_host() -> str:
    """Return the bind host from ``API_HOST`` or the named default."""
    return os.environ.get(HOST_ENV_VAR, DEFAULT_API_HOST)


def resolve_cors_origins() -> list[str]:
    """Return the CORS allow-list from ``CORS_ORIGINS`` or the UI dev default.

    Config-driven (guideline §7.2): the value is a comma-separated list of
    browser origins; each entry is trimmed and blanks dropped. With the env var
    unset (or empty) it falls back to the single named :data:`DEFAULT_UI_ORIGIN`
    so local development works out of the box without leaking a wildcard.
    """
    raw = os.environ.get(CORS_ORIGINS_ENV_VAR)
    if raw is None or not raw.strip():
        return [DEFAULT_UI_ORIGIN]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def resolve_port() -> int:
    """Return the bind port from ``API_PORT`` or the named default."""
    raw = os.environ.get(PORT_ENV_VAR)
    if raw is None or not raw.strip():
        return DEFAULT_API_PORT
    return int(raw)
