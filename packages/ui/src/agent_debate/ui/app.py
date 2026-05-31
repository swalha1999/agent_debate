"""FastAPI application factory for the agent_debate UI (task 11.1, issue #73).

PRD §6: a lightweight web frontend over the API. This task is the *topic input
page*: ``GET /`` serves a clean, accessible page with a topic ``<input>`` and a
"Start debate" button; the page's JS posts the topic to the API's
``POST /debates`` and shows the returned ``run_id`` (the live transcript view is
task 11.2).

Config-driven API base URL (guideline §7.2): the UI never hard-codes where the
API lives. The base URL (from :func:`resolve_api_base_url`) is both *injected*
into the served HTML (a placeholder swap, so the page works with zero extra
round-trips) and exposed via ``GET /config`` (JSON, for tests + a programmatic
reader). The HTML/CSS/JS are static assets served from ``static/`` — not Python,
so they sit outside pytest coverage; the serving routes here are what's tested.
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.core import __version__
from agent_debate.log import get_logger
from agent_debate.ui.config import resolve_api_base_url
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

#: Human-readable service identifier.
SERVICE_NAME = "agent_debate.ui"

#: ``run_id`` namespacing this surface's structured log emissions.
_LOG_RUN_ID = "ui.app"

#: Directory holding the static frontend (index template + CSS/JS).
_STATIC_DIR = Path(__file__).parent / "static"

#: Placeholder in ``index.html`` swapped for the config-driven API base URL.
_API_BASE_URL_PLACEHOLDER = "__API_BASE_URL__"


def _render_index() -> str:
    """Return the index HTML with the config-driven API base URL injected."""
    template = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return template.replace(_API_BASE_URL_PLACEHOLDER, resolve_api_base_url())


def _register_routes(app: FastAPI) -> None:
    """Attach the page + config routes and mount the static assets."""

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        """Serve the topic-input page (API base URL injected)."""
        return _render_index()

    @app.get("/config")
    async def config() -> dict[str, str]:
        """Expose the config-driven API base URL for the page's JS."""
        return {"api_base_url": resolve_api_base_url()}

    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


def create_app() -> FastAPI:
    """Build and return a fresh FastAPI app serving the UI.

    App-factory pattern (mirrors the API): each call returns an independent
    instance so tests and deployments stay isolated.
    """
    app = FastAPI(
        title=SERVICE_NAME,
        version=__version__,
        summary="Lightweight web UI over the agent_debate API (PRD §6).",
    )
    _register_routes(app)
    get_logger(_LOG_RUN_ID).info("ui_app_created", service=SERVICE_NAME, version=__version__)
    return app


#: Module-level instance for ``uvicorn agent_debate.ui.app:app``.
app = create_app()
