"""Debate endpoints — ``POST /debates`` + ``GET /debates/{id}`` (task 10.2, #69).

PRD §6. ``POST /debates`` validates the request, mints a ``run_id``, registers a
``running`` record in the in-memory :class:`~agent_debate.api.debate_store.
DebateStore`, schedules the actual run on a FastAPI ``BackgroundTasks`` worker
and returns ``{run_id, status}`` immediately (HTTP 201). The worker drives the
injected runner (the SDK in production, a stub in tests) and flips the record to
``done`` or ``failed``. ``GET /debates/{id}`` returns that record's status and,
once complete, the :class:`~agent_debate.core.DebateResult`; an unknown id is a
``404``.

Concurrency choice (documented): one in-process store + a per-request background
worker. Full SSE streaming (10.3) and durable persistence are out of scope.
"""

from __future__ import annotations

import uuid

from agent_debate.api.debate_models import DebateRequest, DebateStarted, DebateState
from agent_debate.api.debate_runner import DebateRunner, get_debate_runner
from agent_debate.api.debate_store import DebateStore
from agent_debate.log import get_logger
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

#: ``run_id`` namespacing this surface's structured log emissions.
_LOG_RUN_ID = "api.debates"

_LOG = get_logger(_LOG_RUN_ID)


def _run_debate(
    store: DebateStore, runner: DebateRunner, run_id: str, request: DebateRequest
) -> None:
    """Background worker: run the debate and record done/failed (no raise)."""
    try:
        result = runner(request.topic, request.overrides())
    except Exception as exc:  # noqa: BLE001 — record any failure, never crash the worker.
        store.mark_failed(run_id, str(exc))
        _LOG.warning("debate_run_failed", debate_run_id=run_id, error=str(exc))
        return
    store.mark_done(run_id, result)
    _LOG.info("debate_run_done", debate_run_id=run_id)


def create_debate_router(store: DebateStore) -> APIRouter:
    """Build the debate router bound to ``store`` (the per-app job state)."""
    router = APIRouter(prefix="/debates", tags=["debates"])

    @router.post("", status_code=status.HTTP_201_CREATED)
    async def start_debate(
        request: DebateRequest, background: BackgroundTasks, http_request: Request
    ) -> DebateStarted:
        """Validate + start a debate; return its ``run_id`` and initial status."""
        run_id = uuid.uuid4().hex
        record = store.create(run_id)
        runner = get_debate_runner(http_request.app)
        background.add_task(_run_debate, store, runner, run_id, request)
        _LOG.info("debate_run_started", debate_run_id=run_id)
        return DebateStarted(run_id=run_id, status=record.status)

    @router.get("/{run_id}")
    async def get_debate(run_id: str) -> DebateState:
        """Return the run's status and, once complete, its result."""
        record = store.get(run_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No debate found for run_id {run_id!r}.",
            )
        return DebateState(
            run_id=record.run_id,
            status=record.status,
            result=record.result,
            error=record.error,
        )

    return router


__all__ = ["create_debate_router"]
