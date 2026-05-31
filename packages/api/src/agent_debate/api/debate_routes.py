"""Debate endpoints — start, status, and SSE stream (tasks 10.2/10.3, #69/#70).

PRD §6. ``POST /debates`` validates the request, mints a ``run_id``, registers a
``running`` record in the in-memory :class:`~agent_debate.api.debate_store.
DebateStore`, schedules the actual run on a FastAPI ``BackgroundTasks`` worker
and returns ``{run_id, status}`` immediately (HTTP 201). The worker drives the
injected streaming runner (the SDK in production, a stub in tests), publishing
each ordered, typed event into the record's per-run buffer and flipping the
record to ``done``/``failed``. ``GET /debates/{id}`` returns that record's status
and, once complete, the :class:`~agent_debate.core.DebateResult`.

``GET /debates/{id}/stream`` (10.3) streams that buffer as Server-Sent Events for
live consumers: a plain :class:`~fastapi.responses.StreamingResponse` with media
type ``text/event-stream`` (no new dependency), one record per event
(``event: <event_type>``, ``data: <json>``), live for a running debate and a
faithful replay for a finished one, terminated by a ``done`` sentinel. An unknown
id is a ``404``.

Concurrency choice (documented): one in-process store + a per-request background
worker; the per-run :class:`~agent_debate.api.event_buffer.EventBuffer` is the
thread-safe hand-off from worker to SSE consumer. Durable persistence is out of
scope.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

from agent_debate.api.debate_models import DebateRequest, DebateStarted, DebateState
from agent_debate.api.debate_store import DebateRecord, DebateStore
from agent_debate.api.preflight import get_preflight
from agent_debate.api.sse import SSE_MEDIA_TYPE, format_done, format_log_event
from agent_debate.api.stream_runner import DebateStreamRunner, get_stream_runner
from agent_debate.log import get_logger
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.responses import StreamingResponse

#: ``run_id`` namespacing this surface's structured log emissions.
_LOG_RUN_ID = "api.debates"

_LOG = get_logger(_LOG_RUN_ID)


def _run_debate(
    store: DebateStore,
    runner: DebateStreamRunner,
    record: DebateRecord,
    request: DebateRequest,
) -> None:
    """Background worker: run the debate, publishing events, record done/failed.

    Drives the streaming runner so each event is pushed into ``record.events``
    (the SSE buffer) live; ``mark_done``/``mark_failed`` then close that buffer so
    any attached stream terminates. Never raises (the worker must not crash).
    """
    run_id = record.run_id
    try:
        result = runner(request.topic, request.overrides(), record.events.publish, run_id)
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
        """Validate + start a debate; return its ``run_id`` and initial status.

        Runs the synchronous preflight first (e.g. provider-key validation) so a
        misconfiguration fails the request with a clear, safe error *before* a
        doomed run is scheduled — the error handlers map it to a consistent
        envelope (a missing key -> 503; anything unexpected -> 500). The
        background worker, by contrast, only handles faults *during* a run.
        """
        get_preflight(http_request.app)()
        run_id = uuid.uuid4().hex
        record = store.create(run_id)
        runner = get_stream_runner(http_request.app)
        background.add_task(_run_debate, store, runner, record, request)
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

    @router.get("/{run_id}/stream")
    async def stream_debate(run_id: str) -> StreamingResponse:
        """Stream the run's events live (or replay a finished run) via SSE.

        Drains the run's :class:`~agent_debate.api.event_buffer.EventBuffer`,
        yielding each ordered, typed event as an SSE record, then a terminal
        ``done`` event that closes the stream. Unknown ``run_id`` is a 404.
        """
        record = store.get(run_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No debate found for run_id {run_id!r}.",
            )
        return StreamingResponse(_sse_events(record), media_type=SSE_MEDIA_TYPE)

    return router


def _sse_events(record: DebateRecord) -> Iterator[str]:
    """Yield each buffered event as an SSE record, then the ``done`` sentinel."""
    for event in record.events.stream():
        yield format_log_event(event)
    yield format_done({"run_id": record.run_id, "status": record.status})


__all__ = ["create_debate_router"]
