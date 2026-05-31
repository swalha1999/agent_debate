"""Config-driven host/port + API base URL for the UI server (task 11.1, #73).

No hard-coded values scattered through the code (guideline §7.2): the Uvicorn
bind address comes from ``UI_HOST`` / ``UI_PORT`` and the API base URL the
browser-side JS talks to comes from ``API_BASE_URL`` — each falling back to a
single named constant. One tiny module gives the app, the page template and the
entrypoint one source of truth.
"""

from __future__ import annotations

import os

#: Default bind host — localhost-only, the safe default for a dev surface.
DEFAULT_UI_HOST = "127.0.0.1"

#: Default bind port for the UI server (Vite's default dev port, PRD §6).
DEFAULT_UI_PORT = 5173

#: Default base URL of the API the browser-side JS calls. Matches the API's own
#: ``DEFAULT_API_HOST``/``DEFAULT_API_PORT``; production sets ``API_BASE_URL``.
DEFAULT_API_BASE_URL = "http://localhost:8000"

#: Env var names (single source of truth, never inline string literals).
HOST_ENV_VAR = "UI_HOST"
PORT_ENV_VAR = "UI_PORT"
API_BASE_URL_ENV_VAR = "API_BASE_URL"


def resolve_host() -> str:
    """Return the bind host from ``UI_HOST`` or the named default."""
    return os.environ.get(HOST_ENV_VAR, DEFAULT_UI_HOST)


def resolve_port() -> int:
    """Return the bind port from ``UI_PORT`` or the named default."""
    raw = os.environ.get(PORT_ENV_VAR)
    if raw is None or not raw.strip():
        return DEFAULT_UI_PORT
    return int(raw)


def resolve_api_base_url() -> str:
    """Return the API base URL from ``API_BASE_URL`` or the named default.

    Config-driven (guideline §7.2): this is the origin the page's JS posts the
    new debate to. With the env var unset (or blank) it falls back to the single
    named :data:`DEFAULT_API_BASE_URL` so local development works out of the box.
    """
    raw = os.environ.get(API_BASE_URL_ENV_VAR)
    if raw is None or not raw.strip():
        return DEFAULT_API_BASE_URL
    return raw.strip()
