"""Uvicorn entrypoint for the agent_debate UI (task 11.1, issue #73).

Serves the FastAPI app via Uvicorn on a config-driven host/port (resolved from
``UI_HOST`` / ``UI_PORT`` env or named-constant defaults — never inline magic).
Exposed both as ``python -m agent_debate.ui`` and the ``agent-debate-ui``
console script (see ``pyproject.toml``).
"""

from __future__ import annotations

import uvicorn
from agent_debate.log import get_logger
from agent_debate.ui.app import app
from agent_debate.ui.config import resolve_host, resolve_port

#: ``run_id`` namespacing this surface's startup log emissions.
_LOG_RUN_ID = "ui.server"


def run_server() -> None:
    """Serve the app via Uvicorn on the config-driven host/port."""
    host = resolve_host()
    port = resolve_port()
    get_logger(_LOG_RUN_ID).info("ui_server_starting", host=host, port=port)
    uvicorn.run(app, host=host, port=port)


def main() -> None:
    """Console-script / ``python -m`` entrypoint."""
    run_server()


if __name__ == "__main__":  # pragma: no cover — process entrypoint guard.
    main()
