"""agent_debate API (``agent_debate.api``) — FastAPI surface (PRD §6).

A thin FastAPI shell over the ``core`` SDK. This package exposes the app factory
:func:`create_app` and a module-level ``app`` for Uvicorn (task 10.1); the
debate endpoints (10.2), SSE stream (10.3) and CORS/validation (10.4) build on
top of it.

``api`` depends on both ``core`` and ``log`` (issue #3): it re-exports their
versions by importing across the edges, proving the dependencies resolve at
runtime.
"""

from __future__ import annotations

from agent_debate.api.app import app, create_app
from agent_debate.api.debate_runner import DebateRunner, set_debate_runner
from agent_debate.api.debate_store import DebateStatus
from agent_debate.api.errors import ErrorType, register_exception_handlers
from agent_debate.api.preflight import Preflight, set_preflight
from agent_debate.api.stream_runner import DebateStreamRunner, set_stream_runner
from agent_debate.core import core_version
from agent_debate.log import log_version

#: Version of the API surface.
LIBRARY_VERSION = "1.00"

__all__ = [
    "LIBRARY_VERSION",
    "DebateRunner",
    "DebateStatus",
    "DebateStreamRunner",
    "ErrorType",
    "Preflight",
    "app",
    "core_version",
    "create_app",
    "log_version",
    "register_exception_handlers",
    "set_debate_runner",
    "set_preflight",
    "set_stream_runner",
]
