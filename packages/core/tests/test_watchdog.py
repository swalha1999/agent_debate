"""Unit tests for the keep-alive Watchdog (issue #216, HW2 §8.6).

HW2 §8.6 — *Watchdog with keep-alive*: a fallen (hung/dead/stopped-beating)
worker process must be DETECTED, KILLED and RESTARTED, in addition to the
per-turn timeout + retry seam (which guards a single model call). This module
drives that behaviour TDD-first (red before green).

Determinism: the Watchdog's clock (``monotonic``) and ``sleep`` are injected, so
no real time passes. A fake worker reports its liveness via an injected
heartbeat source; a "fallen" worker simply stops advancing its heartbeat (or
raises), and the Watchdog must observe the stale beat past ``liveness_timeout_s``
and restart it. Config *values* come from an in-test
:class:`~agent_debate.core.watchdog.WatchdogConfig`, so nothing is hard-coded.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from agent_debate.core.watchdog import Watchdog, WatchdogConfig, load_watchdog_config


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Parse every non-blank line of a JSONL file into a list of dicts."""
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _config(
    *, heartbeat_interval_s: float = 1.0, liveness_timeout_s: float = 3.0, max_restarts: int = 2
) -> WatchdogConfig:
    """Build a watchdog config with the given knobs (no hard-coded values)."""
    return WatchdogConfig.model_validate(
        {
            "version": "1.00",
            "heartbeat_interval_s": heartbeat_interval_s,
            "liveness_timeout_s": liveness_timeout_s,
            "max_restarts": max_restarts,
        }
    )


class FakeClock:
    """Deterministic injectable clock: ``monotonic`` advances on each ``sleep``."""

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakeWorker:
    """A simulated long-running worker that beats a heartbeat while alive.

    ``last_beat`` is the monotonic time of its most recent keep-alive. A healthy
    worker advances it every tick; a *fallen* worker stops (``alive=False``), so
    its heartbeat goes stale and the Watchdog must restart it. Each restart
    records a ``(start_time)`` entry in :attr:`starts`.
    """

    def __init__(self, clock: FakeClock, *, fall_after: int | None = None) -> None:
        self._clock = clock
        self._fall_after = fall_after
        self.last_beat = 0.0
        self.alive = True
        self.ticks = 0
        self.starts: list[float] = []
        self.kills: list[float] = []

    def start(self) -> None:
        self.alive = True
        self.ticks = 0
        self.last_beat = self._clock.monotonic()
        self.starts.append(self._clock.monotonic())

    def kill(self) -> None:
        self.alive = False
        self.kills.append(self._clock.monotonic())

    def heartbeat(self) -> float:
        """Advance + return the heartbeat if still alive (else it goes stale)."""
        if self.alive:
            self.ticks += 1
            if self._fall_after is not None and self.ticks >= self._fall_after:
                self.alive = False  # the worker "falls" and stops beating
            else:
                self.last_beat = self._clock.monotonic()
        return self.last_beat


def _build(
    worker: FakeWorker, clock: FakeClock, config: WatchdogConfig, runs_dir: Path
) -> Watchdog:
    return Watchdog(
        config=config,
        start=worker.start,
        kill=worker.kill,
        heartbeat=worker.heartbeat,
        run_id="wd-test",
        runs_dir=runs_dir,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )


def test_healthy_worker_is_not_restarted(tmp_path: Path) -> None:
    """A worker that keeps beating runs to completion with NO restart."""
    clock = FakeClock()
    worker = FakeWorker(clock)  # never falls
    config = _config(max_restarts=2)
    watchdog = _build(worker, clock, config, tmp_path)

    result = watchdog.run(max_ticks=5)

    assert result.restarts == 0
    assert result.fell is False
    assert len(worker.starts) == 1  # started once, never restarted


def test_fallen_worker_is_detected_killed_and_restarted(tmp_path: Path) -> None:
    """A worker whose heartbeat goes stale is detected, killed and restarted."""
    clock = FakeClock()
    worker = FakeWorker(clock, fall_after=2)
    # interval 1.0s, timeout 1.5s: once the worker stops beating after tick 2,
    # the next check (1.0s later) is already stale (>1.5s since last beat by the
    # following tick), so the fall is detected and a restart issued.
    config = _config(heartbeat_interval_s=1.0, liveness_timeout_s=1.5, max_restarts=3)
    watchdog = _build(worker, clock, config, tmp_path)

    result = watchdog.run(max_ticks=6)

    assert result.restarts >= 1
    assert len(worker.kills) >= 1  # the fallen worker was killed
    assert len(worker.starts) >= 2  # started, then restarted at least once


def test_gives_up_after_max_restarts(tmp_path: Path) -> None:
    """A worker that always falls is restarted at most ``max_restarts`` times."""
    clock = FakeClock()

    class AlwaysFalls(FakeWorker):
        def heartbeat(self) -> float:
            # never advances last_beat past the start -> always goes stale
            return self.last_beat

    worker = AlwaysFalls(clock)
    config = _config(liveness_timeout_s=2.0, max_restarts=2)
    watchdog = _build(worker, clock, config, tmp_path)

    result = watchdog.run(max_ticks=50)

    assert result.fell is True
    assert result.restarts == config.max_restarts  # gave up after N


def test_events_are_logged_for_detect_and_restart(tmp_path: Path) -> None:
    """Each detect/restart emits a structured watchdog system event."""
    clock = FakeClock()
    worker = FakeWorker(clock, fall_after=1)
    config = _config(liveness_timeout_s=2.0, max_restarts=2)
    watchdog = _build(worker, clock, config, tmp_path)

    watchdog.run(max_ticks=10)

    events = _read_jsonl(tmp_path / "wd-test.jsonl")
    watchdog_events = [e for e in events if e.get("payload", {}).get("watchdog")]
    assert watchdog_events  # at least one watchdog event was logged
    assert all(e["event_type"] == "system" for e in watchdog_events)
    tags = {e["payload"]["watchdog"] for e in watchdog_events}
    assert "restart" in tags


def test_load_watchdog_config_from_repo_file() -> None:
    """The packaged ``config/watchdog.json`` loads + validates."""
    config = load_watchdog_config()
    assert config.version
    assert config.heartbeat_interval_s > 0
    assert config.liveness_timeout_s > 0
    assert config.max_restarts >= 0


def test_config_rejects_nonpositive_timeout() -> None:
    """A non-positive liveness timeout is rejected at validation."""
    with pytest.raises(ValueError, match="liveness_timeout_s|greater than"):
        _config(liveness_timeout_s=0.0)
