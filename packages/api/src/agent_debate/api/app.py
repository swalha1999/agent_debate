"""FastAPI application factory for the agent_debate API (task 10.1, issue #68).

PRD §6: a thin FastAPI shell over the ``core`` SDK. This task wires only the
skeleton — a :func:`create_app` factory (config-driven, reusable) plus health
and root endpoints. The debate endpoints (10.2), SSE stream (10.3) and
CORS/validation (10.4) land in later tasks.

The app holds process :class:`~agent_debate.core.Settings` (via
:func:`get_settings`) so downstream routes can construct a
:class:`~agent_debate.core.DebateEngine`; every model/API call the SDK makes
routes through the Epic-13 gatekeeper, so the API adds no new external edges.
"""

from __future__ import annotations

from agent_debate.core import __version__, get_settings
from agent_debate.log import get_logger
from fastapi import FastAPI

#: Human-readable service identifier surfaced by the root endpoint.
SERVICE_NAME = "agent_debate.api"

#: ``run_id`` used to namespace this surface's structured log emissions.
_LOG_RUN_ID = "api.app"


def _register_routes(app: FastAPI) -> None:
    """Attach the skeleton routes (health + service-info root) to ``app``."""

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Liveness probe: ``{"status": "ok", "version": <sdk version>}``."""
        return {"status": "ok", "version": __version__}

    @app.get("/")
    async def root() -> dict[str, str]:
        """Service info for the API root."""
        return {"service": SERVICE_NAME, "version": __version__}


def create_app() -> FastAPI:
    """Build and return a fresh FastAPI app wired to the SDK.

    App-factory pattern: each call returns an independent instance so tests and
    deployments stay isolated. Settings are loaded once here (config-driven) and
    stashed on ``app.state`` for the debate routes added by later tasks.
    """
    settings = get_settings()
    app = FastAPI(
        title=SERVICE_NAME,
        version=__version__,
        summary="FastAPI surface over the agent_debate SDK (PRD §6).",
    )
    app.state.settings = settings
    _register_routes(app)

    get_logger(_LOG_RUN_ID).info("api_app_created", service=SERVICE_NAME, version=__version__)
    return app


#: Module-level instance for ``uvicorn agent_debate.api.app:app``.
app = create_app()
