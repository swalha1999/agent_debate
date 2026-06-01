"""Keep-alive Watchdog: detect a fallen worker, kill it, restart it (#216, §8.6).

HW2 §8.6 — *Watchdog with keep-alive*: a long-running worker/agent process can
**fall** (hang, die, or simply stop beating) without raising an error a single
call would catch. The Watchdog monitors that worker's liveness via a keep-alive
heartbeat and, when the heartbeat goes stale beyond ``liveness_timeout_s``,
**kills** the worker and **restarts** it — up to ``max_restarts`` times, after
which it gives up. Every action is logged via the LOG package as a ``system``
event tagged with its watchdog action.

This is DISTINCT from the per-turn timeout + retry seam
(:mod:`agent_debate.core.engine._call`): that wrapper bounds and retries a
*single* model call (``execute``), failing the turn after its budget. The
Watchdog guards a *longer-running unit of work / process* by liveness, not by a
single call's wall-clock — the two compose, they do not overlap.

Determinism: the clock (``monotonic``) and ``sleep`` are injected seams, and the
worker is driven through injected ``start``/``kill``/``heartbeat`` callables, so
tests run fast with no real threads/sleeping and no real timing. No interval/
timeout/restart value is hard-coded — all arrive from :class:`WatchdogConfig`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from agent_debate.core import constants
from agent_debate.core.engine.stream import EventSink, emit_event
from agent_debate.core.watchdog._config import WatchdogConfig


@dataclass(frozen=True)
class WatchdogResult:
    """Outcome of a :meth:`Watchdog.run` supervision loop.

    Attributes:
        restarts: How many times the worker was killed and restarted.
        fell: ``True`` if the worker was still down when the loop ended after
            exhausting ``max_restarts`` (the Watchdog gave up); ``False`` if it
            finished healthy (no fall, or the last restart recovered it).
        ticks: How many liveness checks the loop performed.
    """

    restarts: int
    fell: bool
    ticks: int


class Watchdog:
    """Monitors a worker's keep-alive heartbeat; restarts it when it falls (§8.6).

    The worker is supplied as three callables so the Watchdog stays provider- and
    architecture-agnostic: ``start`` (launch/relaunch the worker), ``kill``
    (forcibly stop a hung/fallen worker) and ``heartbeat`` (return the monotonic
    timestamp of the worker's most recent keep-alive). A heartbeat that has not
    advanced within ``liveness_timeout_s`` means the worker has fallen.
    """

    def __init__(  # noqa: PLR0913 — explicit injected seams (no shared state).
        self,
        *,
        config: WatchdogConfig,
        start: Callable[[], None],
        kill: Callable[[], None],
        heartbeat: Callable[[], float],
        run_id: str,
        runs_dir: Path | str,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        sink: EventSink | None = None,
    ) -> None:
        """Wire the Watchdog to a worker and its config.

        Args:
            config: Liveness knobs (interval/timeout/max-restarts) — never inlined.
            start: Launches (or relaunches) the supervised worker.
            kill: Forcibly stops a fallen worker before a restart.
            heartbeat: Returns the monotonic time of the worker's last keep-alive.
            run_id: The run id stamped on every emitted event.
            runs_dir: Directory holding the per-run JSONL sink.
            monotonic: Injected clock; defaults to :func:`time.monotonic`.
            sleep: Injected wait between checks; defaults to :func:`time.sleep`.
            sink: Optional live event sink; ``None`` logs only.
        """
        self._config = config
        self._start = start
        self._kill = kill
        self._heartbeat = heartbeat
        self._run_id = run_id
        self._runs_dir = runs_dir
        self._monotonic = monotonic
        self._sleep = sleep
        self._sink = sink

    def run(self, *, max_ticks: int) -> WatchdogResult:
        """Supervise the worker for up to ``max_ticks`` liveness checks (§8.6).

        Starts the worker, then on each tick waits ``heartbeat_interval_s`` and
        reads the keep-alive. If the heartbeat is stale beyond
        ``liveness_timeout_s`` the worker has *fallen*: it is killed and (while
        restarts remain) restarted; otherwise the Watchdog gives up. ``max_ticks``
        bounds the loop so a healthy worker's supervision terminates.

        Args:
            max_ticks: Maximum number of liveness checks before stopping.

        Returns:
            A :class:`WatchdogResult` recording restarts, whether it fell, and the
            tick count.
        """
        self._start()
        restarts = 0
        for tick in range(1, max_ticks + 1):
            self._sleep(self._config.heartbeat_interval_s)
            if self._is_alive():
                continue
            self._emit(constants.WATCHDOG_ACTION_DETECT, restarts=restarts, tick=tick)
            self._kill()
            self._emit(constants.WATCHDOG_ACTION_KILL, restarts=restarts, tick=tick)
            if restarts >= self._config.max_restarts:
                self._emit(constants.WATCHDOG_ACTION_GIVE_UP, restarts=restarts, tick=tick)
                return WatchdogResult(restarts=restarts, fell=True, ticks=tick)
            restarts += 1
            self._start()
            self._emit(constants.WATCHDOG_ACTION_RESTART, restarts=restarts, tick=tick)
        return WatchdogResult(restarts=restarts, fell=False, ticks=max_ticks)

    def _is_alive(self) -> bool:
        """Return ``True`` while the last keep-alive is within the liveness window.

        A worker that hangs/dies/stops beating leaves ``heartbeat()`` stale; once
        ``now - last_beat`` exceeds ``liveness_timeout_s`` it counts as fallen. A
        ``heartbeat`` that itself raises is treated as a fall (the worker is gone).
        """
        try:
            last_beat = self._heartbeat()
        except Exception:  # noqa: BLE001 — any heartbeat failure means it fell.
            return False
        return (self._monotonic() - last_beat) <= self._config.liveness_timeout_s

    def _emit(self, action: str, *, restarts: int, tick: int) -> None:
        """Log one ``system`` Watchdog event tagged with ``action`` (§8.6)."""
        emit_event(
            self._sink,
            run_id=self._run_id,
            agent=constants.WATCHDOG_LOG_AGENT,
            event_type=constants.WATCHDOG_EVENT_TYPE,
            round=constants.WATCHDOG_ROUND,
            payload={constants.WATCHDOG_EVENT_TAG: action, "restarts": restarts, "tick": tick},
            runs_dir=self._runs_dir,
        )


__all__ = ["Watchdog", "WatchdogResult"]
