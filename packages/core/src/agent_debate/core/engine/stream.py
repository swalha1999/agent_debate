"""Live event STREAMING surface for the engine (issue #51, task 6.6, §6).

Orchestration sub-PRD §6: the engine's events (``message | tool_call | nudge |
timeout | retry | verdict | system``) are "consumed live by CLI/API/UI". Until
now the engine only *logged* each event to ``runs/<run_id>.jsonl`` and returned
the final :class:`~agent_debate.core.engine.result.DebateResult`; this module
adds the live STREAM so CLI (Epic 9) / API SSE (Epic 10) / UI (Epic 11) can render
as the debate happens.

Design — one event schema, one emit point. The streamed event IS the LOG event
(:class:`~agent_debate.log.LogEvent`, already typed + JSON-serialisable for SSE).
The sink primitives (:class:`EventSink`, :class:`CollectingSink`, :func:`emit_event`)
live in the LOG package — the single build+log+emit chokepoint — and are re-exported
here as the engine's streaming surface. Every engine site that logs an event uses
:func:`emit_event`, so it streams the SAME validated record, in the SAME order,
never built twice. The sink is OPT-IN: ``sink=None`` (the default) changes nothing.

:func:`stream_debate` is a thin GENERATOR wrapper on top of the sink: it runs the
debate on a worker thread, the threaded sink pushes each emitted event onto a
queue, and the generator yields events live (then the final ``DebateResult``).
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agent_debate.log import DEFAULT_RUNS_DIR, CollectingSink, EventSink, LogEvent, emit_event

if TYPE_CHECKING:
    from agent_debate.core.engine.gatekeeper_proto import Gatekeeper
    from agent_debate.core.engine.models import DebateConfig
    from agent_debate.core.engine.result import DebateResult
    from agent_debate.core.engine.setup import DebateSetup

#: Sentinel pushed onto the queue to signal the worker thread has finished.
_DONE: LogEvent = LogEvent.model_construct(run_id="", round=0, agent="", event_type="system")


def stream_debate(
    setup: DebateSetup,
    config: DebateConfig,
    *,
    gatekeeper: Gatekeeper | None = None,
    run_id: str,
    runs_dir: Path | str = DEFAULT_RUNS_DIR,
) -> Iterator[LogEvent | DebateResult]:
    """Run a debate on a worker thread, yielding each event live then the result.

    A generator wrapper over the :class:`EventSink` mechanism: the debate runs on a
    background thread whose sink pushes every emitted event onto a queue, and this
    generator yields them in order as they happen. The FINAL item yielded is the
    completed :class:`~agent_debate.core.engine.result.DebateResult` (so a consumer
    can both render live and capture the full result).

    Args:
        setup: The prepared run state (agents, isolated contexts, topic, sides).
        config: The run config (``rounds`` and ``max_words`` drive the loop).
        gatekeeper: The API gatekeeper to route model calls through (Epic 13).
        run_id: The run id stamped on every emitted event.
        runs_dir: Directory holding the per-run JSONL sink.

    Yields:
        Each :class:`~agent_debate.log.LogEvent` as it happens, then the final
        :class:`~agent_debate.core.engine.result.DebateResult`.
    """
    from agent_debate.core.engine.loop import run_debate_loop

    events: queue.Queue[LogEvent] = queue.Queue()
    box: dict[str, Any] = {}

    def _push(event: LogEvent) -> None:
        events.put(event)

    def _run() -> None:
        try:
            box["result"] = run_debate_loop(
                setup,
                config,
                gatekeeper=gatekeeper,
                run_id=run_id,
                runs_dir=runs_dir,
                sink=_push,
            )
        except BaseException as exc:  # noqa: BLE001 — surfaced to the caller below.
            box["error"] = exc
        finally:
            events.put(_DONE)

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()
    while True:
        item = events.get()
        if item is _DONE:
            break
        yield item
    worker.join()
    if "error" in box:
        raise box["error"]
    yield box["result"]


__all__ = ["CollectingSink", "EventSink", "emit_event", "stream_debate"]
