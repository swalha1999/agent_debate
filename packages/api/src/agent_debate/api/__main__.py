"""Uvicorn entrypoint for the agent_debate API (task 10.1, issue #68).

Runs the FastAPI app via Uvicorn on a config-driven host/port (resolved from
``API_HOST`` / ``API_PORT`` env or named-constant defaults — never inline
magic). Exposed both as ``python -m agent_debate.api`` and the
``agent-debate-api`` console script (see ``pyproject.toml``).
"""

from __future__ import annotations

import uvicorn
from agent_debate.api.app import app
from agent_debate.api.config import resolve_host, resolve_port
from agent_debate.log import get_logger

#: ``run_id`` namespacing this surface's startup log emissions.
_LOG_RUN_ID = "api.server"


def run_server() -> None:
    """Serve the app via Uvicorn on the config-driven host/port."""
    host = resolve_host()
    port = resolve_port()
    get_logger(_LOG_RUN_ID).info("api_server_starting", host=host, port=port)
    uvicorn.run(app, host=host, port=port)


def main() -> None:
    """Console-script / ``python -m`` entrypoint."""
    run_server()


if __name__ == "__main__":  # pragma: no cover — process entrypoint guard.
    main()
