"""Unit tests for the full queue-status snapshot (TASKS.md 13.5, issue #94).

Sub-PRD ``docs/prds/api-gatekeeper.md`` §3/§6: ``get_queue_status()`` reports the
overflow queue **depth + stats** so queue pressure is observable. Task 13.5 makes
that snapshot **complete and accurate** (per-service + aggregate: depth,
max_depth from config, lifetime enqueued/drained/backpressure, live in-flight)
and **surfaces it to the run log** via :meth:`ApiGatekeeper.log_queue_status`.

Written TDD-first (red before green). An injected fake clock makes "the window
is exhausted" deterministic; all limit *values* and the queue depth come from a
:class:`RateLimitConfig` built in-test, so nothing is hard-coded.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest
from agent_debate.core.gatekeeper import (
    ApiGatekeeper,
    GatekeeperStatus,
    QueueFullError,
    QueueStatus,
    RateLimitConfig,
)


class _FakeClock:
    """A monotonic clock the test advances explicitly."""

    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def _config(
    *,
    requests_per_minute: int = 30,
    requests_per_hour: int = 500,
    concurrent_max: int = 5,
    queue_max_depth: int = 100,
) -> RateLimitConfig:
    """Build a one-service (``default``) config with the given limits/depth."""
    return RateLimitConfig.model_validate(
        {
            "version": "1.00",
            "services": {
                "default": {
                    "requests_per_minute": requests_per_minute,
                    "requests_per_hour": requests_per_hour,
                    "concurrent_max": concurrent_max,
                    "retry_after_seconds": 30,
                    "max_retries": 3,
                    "queue_max_depth": queue_max_depth,
                }
            },
        }
    )


def _gatekeeper(config: RateLimitConfig, clock: _FakeClock, tmp_path: Path) -> ApiGatekeeper:
    """Build a gatekeeper wired to an injectable clock + tmp log sink."""
    return ApiGatekeeper(config, run_id="run-s", runs_dir=tmp_path, time_fn=clock)


def test_status_reports_depth_and_counts(tmp_path: Path) -> None:
    """After executes/enqueues/drains the per-service status is accurate."""
    clock = _FakeClock()
    gk = _gatekeeper(_config(requests_per_minute=1, requests_per_hour=100), clock, tmp_path)

    gk.execute(lambda: "a", service="default")  # runs now
    gk.execute(lambda: "b", service="default")  # enqueued
    gk.execute(lambda: "c", service="default")  # enqueued

    status = gk.get_queue_status()
    assert status.depth == 2
    assert status.enqueued_total == 2
    assert status.drained_total == 0
    assert status.backpressure_total == 0

    clock.t += 61.0
    assert gk.drain() == 1
    after = gk.get_queue_status()
    assert after.depth == 1
    assert after.drained_total == 1


def test_status_reports_max_depth_from_config(tmp_path: Path) -> None:
    """``max_depth`` is sourced from config, never a literal."""
    clock = _FakeClock()
    gk = _gatekeeper(_config(queue_max_depth=7), clock, tmp_path)
    assert gk.get_queue_status().max_depth == 7


def test_status_counts_backpressure_rejections(tmp_path: Path) -> None:
    """A full-queue rejection increments ``backpressure_total``."""
    clock = _FakeClock()
    gk = _gatekeeper(
        _config(requests_per_minute=1, requests_per_hour=100, queue_max_depth=1),
        clock,
        tmp_path,
    )

    gk.execute(lambda: None, service="default")  # runs now
    gk.execute(lambda: None, service="default")  # enqueue (queue full)
    with pytest.raises(QueueFullError):
        gk.execute(lambda: None, service="default")  # backpressure

    assert gk.get_queue_status().backpressure_total == 1


def test_status_reports_in_flight(tmp_path: Path) -> None:
    """A call held mid-flight is reflected in ``in_flight`` from live state."""
    clock = _FakeClock()
    gk = _gatekeeper(_config(concurrent_max=5), clock, tmp_path)
    entered = threading.Event()
    release = threading.Event()

    def slow() -> str:
        entered.set()
        release.wait(timeout=2.0)
        return "done"

    worker = threading.Thread(target=lambda: gk.execute(slow, service="default"))
    worker.start()
    assert entered.wait(timeout=2.0)
    assert gk.get_queue_status().in_flight == 1
    release.set()
    worker.join(timeout=2.0)
    assert gk.get_queue_status().in_flight == 0


def test_full_status_aggregates_across_services(tmp_path: Path) -> None:
    """``get_status`` returns per-service entries plus an aggregate snapshot."""
    clock = _FakeClock()
    gk = _gatekeeper(_config(requests_per_minute=1, requests_per_hour=100), clock, tmp_path)

    gk.execute(lambda: "a", service="default")  # runs now
    gk.execute(lambda: "b", service="default")  # enqueued

    full = gk.get_status()
    assert isinstance(full, GatekeeperStatus)
    assert "default" in full.services
    assert isinstance(full.services["default"], QueueStatus)
    assert full.total_depth == 1
    assert full.total_enqueued == 1


def test_status_is_json_serializable(tmp_path: Path) -> None:
    """The status object round-trips through JSON (so API/SSE can send it)."""
    clock = _FakeClock()
    gk = _gatekeeper(_config(requests_per_minute=1, requests_per_hour=100), clock, tmp_path)
    gk.execute(lambda: "a", service="default")
    gk.execute(lambda: "b", service="default")  # enqueued

    full = gk.get_status()
    blob = full.model_dump_json()
    parsed = json.loads(blob)
    assert parsed["total_depth"] == 1
    assert parsed["services"]["default"]["depth"] == 1


def test_log_queue_status_writes_observable_event(tmp_path: Path) -> None:
    """``log_queue_status`` snapshots and emits one readable system event."""
    clock = _FakeClock()
    gk = _gatekeeper(_config(requests_per_minute=1, requests_per_hour=100), clock, tmp_path)
    gk.execute(lambda: "a", service="default")
    gk.execute(lambda: "b", service="default")  # enqueued

    status = gk.log_queue_status()
    assert status.total_depth == 1

    lines = [
        json.loads(line)
        for line in (tmp_path / "run-s" / "run-s.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    status_events = [e for e in lines if e["payload"].get("queue_event") == "status"]
    assert len(status_events) == 1
    payload = status_events[0]["payload"]
    assert payload["total_depth"] == 1
    assert payload["total_enqueued"] == 1
    assert payload["services"]["default"]["depth"] == 1
