"""Per-turn model-call wrapper — timeout + retry/backoff (issue #49, task 6.4).

Orchestration sub-PRD §4: a debater's model call can hang or fail transiently, so
every per-turn call (the seam in :mod:`agent_debate.core.engine.turn`) is wrapped
to (1) bound it by ``config.turn_timeout_s``, **cancelling** on timeout, (2)
**retry** transient failures up to ``config.max_retries`` with exponential
backoff, and (3) after the budget is exhausted, raise :class:`TurnFailedError` so
the turn is marked FAILED and the controller is informed — the debate degrades
gracefully rather than crashing.

Nothing here is duplicated: the timeout reuses the search layer's thread-based
:func:`~agent_debate.core.search.run_with_timeout` (a daemon worker joined for
``timeout_s``; on timeout a :class:`TimeoutError` is raised and the hung worker is
abandoned — the documented "cancel" semantics for the synchronous ``run_sync``
path), and the retry/backoff reuses the gatekeeper's
:func:`~agent_debate.core.gatekeeper._retry.run_with_retry` policy.

Relationship to the gatekeeper's own retry: the call still routes **through**
``gatekeeper.execute`` (every external call does), so the gatekeeper handles the
*rate/throughput* concern; this wrapper composes AROUND ``execute`` to add the
turn-level ``turn_timeout_s`` + turn-failure semantics. They do not double-count —
the gatekeeper retries rate errors inside ``execute``; this wrapper retries
timeouts of the whole ``execute`` call.

No values are hard-coded: ``timeout_s`` + ``max_retries`` come from
:class:`~agent_debate.core.engine.models.DebateConfig`, and the backoff base from
the gatekeeper's ``retry_after_seconds`` (its strategy is the single source of
truth). ``sleep_fn`` and ``timeout_runner`` are injected seams so tests are
deterministic and fast (no real threads/sleeping).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agent_debate.core.engine._call_log import _CallLog
from agent_debate.core.engine.gatekeeper_proto import Gatekeeper
from agent_debate.core.engine.models import DebateConfig
from agent_debate.core.gatekeeper import load_rate_limit_config
from agent_debate.core.gatekeeper._retry import is_transient, run_with_retry
from agent_debate.core.search._timeout import run_with_timeout
from agent_debate.log import EventSink

#: Type of the timeout seam: run a no-arg call, bounded by ``timeout_s`` seconds.
TimeoutRunner = Callable[[Callable[[], Any], float], Any]


def _default_timeout_runner(call: Callable[[], Any], timeout_s: float) -> Any:
    """Default timeout seam: the thread-based :func:`run_with_timeout` helper."""
    return run_with_timeout(call, timeout_s=timeout_s)


class TurnFailedError(RuntimeError):
    """Raised when a turn's model call exhausts its timeout + retry budget (§4).

    Carries the final underlying error so the turn can be marked FAILED and the
    controller informed; the debate handles it gracefully and never crashes.
    """

    def __init__(self, cause: BaseException) -> None:
        super().__init__(f"turn model call failed after retries: {type(cause).__name__}")
        self.cause = cause


def _retry_after_seconds(service: str) -> int:
    """Backoff base (seconds) for ``service`` from the gatekeeper's rate config."""
    return load_rate_limit_config().get_service_limits(service).retry_after_seconds


def generate_turn_output(  # noqa: PLR0913 — explicit per-call deps (no shared state).
    gatekeeper: Gatekeeper,
    api_call: Callable[..., Any],
    *,
    message_history: Any,
    service: str,
    config: DebateConfig,
    run_id: str,
    round_: int,
    agent: str,
    runs_dir: Path | str,
    sleep_fn: Callable[[float], None] = time.sleep,
    timeout_runner: TimeoutRunner = _default_timeout_runner,
    sink: EventSink | None = None,
) -> Any:
    """Run a debater's model call through the gatekeeper under timeout + retry (§4).

    The call routes through ``gatekeeper.execute`` (every external call does),
    bounded by ``config.turn_timeout_s``; a timeout is logged and retried up to
    ``config.max_retries`` with exponential backoff (base from the gatekeeper's
    ``retry_after_seconds``). After the budget is exhausted a
    :class:`TurnFailedError` is raised (a ``system`` event having first informed
    the controller), so the loop marks the turn FAILED and continues.

    Args:
        gatekeeper: The API gatekeeper every model call routes through (Epic 13).
        api_call: The model call to run (e.g. ``agent.run_sync``).
        message_history: The run input forwarded to ``api_call``.
        service: Gatekeeper service key selecting rate limits + backoff base.
        config: Supplies ``turn_timeout_s`` + ``max_retries`` (never hard-coded).
        run_id: The run id stamped on every emitted event.
        round_: The 1-based round the call belongs to.
        agent: The emitting side label (``pro``/``con``).
        runs_dir: Directory holding the per-run JSONL sink.
        sleep_fn: Injected sleep seam invoked with each backoff delay.
        timeout_runner: Injected timeout seam bounding each attempt.
        sink: Optional live event sink (§6, task 6.6); ``None`` logs only.

    Returns:
        The result of ``gatekeeper.execute`` (the model output).

    Raises:
        TurnFailedError: When the timeout + retry budget is exhausted.
    """
    emitter = _CallLog(run_id=run_id, agent=agent, round_=round_, runs_dir=runs_dir, sink=sink)
    retry_after = _retry_after_seconds(service)

    def _attempt() -> Any:
        def _routed() -> Any:
            return gatekeeper.execute(api_call, message_history=message_history, service=service)

        try:
            return timeout_runner(_routed, float(config.turn_timeout_s))
        except TimeoutError as exc:
            emitter.timeout(float(config.turn_timeout_s), exc)
            raise

    try:
        return run_with_retry(
            _attempt,
            max_retries=config.max_retries,
            retry_after_seconds=retry_after,
            sleep_fn=sleep_fn,
            on_retry=lambda n, delay, exc: emitter.retry(n, delay, exc),
        )
    except BaseException as exc:
        # A non-transient error (e.g. bad input) is a caller bug, not a flaky
        # turn — propagate it raw. Only an exhausted transient/timeout budget
        # marks the turn FAILED + informs the controller (§4).
        if not is_transient(exc):
            raise
        emitter.failed(exc)
        raise TurnFailedError(exc) from exc


__all__ = ["TimeoutRunner", "TurnFailedError", "generate_turn_output"]
