"""Consolidated Epic-13 acceptance tests (TASKS.md 13.7, issue #96).

Sub-PRD ``docs/prds/api-gatekeeper.md`` §6 acceptance criteria, exercised
**end-to-end through the public** :class:`ApiGatekeeper` **API** (mirroring how
Epics 1/2 consolidated their acceptance pass). The per-task tests cover each
mechanism in isolation; this module proves the behaviours compose correctly via
``execute`` / ``drain`` / ``get_queue_status``:

* a limit hit **queues** the call (FIFO) — never dropped or crashed;
* the queue **drains** as the injected window resets;
* transient failures **retry to ``max_retries``** then raise;
* a full queue applies **backpressure** (``QueueFullError``);
* ``concurrent_max`` **saturation** never exceeds the cap (over-cap calls enqueue).

Determinism: an injected ``time_fn``/``sleep_fn`` (no real sleeping); logged
events asserted from the tmp ``runs_dir`` JSONL. Limit values come from config.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from _gatekeeper_acceptance_helpers import FakeClock, make_config, make_gatekeeper, read_jsonl
from agent_debate.core.gatekeeper import ApiGatekeeper, QueueFullError


def test_limit_hit_queues_call_never_dropped(tmp_path: Path) -> None:
    """Exceeding the per-minute limit enqueues the call (no drop, no crash)."""
    clock = FakeClock()
    gk = make_gatekeeper(make_config(requests_per_minute=1, requests_per_hour=100), clock, tmp_path)
    ran: list[str] = []

    assert gk.execute(lambda: ran.append("a"), service="default") is None or ran == ["a"]
    assert gk.execute(lambda: ran.append("b"), service="default") is None  # queued

    assert ran == ["a"]  # the overflowing call did not run now
    status = gk.get_queue_status()
    assert status.depth == 1 and status.enqueued_total == 1 and status.backpressure_total == 0


def test_queue_drains_as_window_resets(tmp_path: Path) -> None:
    """Advancing the injected clock past the window lets ``drain`` run the queued call."""
    clock = FakeClock()
    gk = make_gatekeeper(make_config(requests_per_minute=1, requests_per_hour=100), clock, tmp_path)
    ran: list[str] = []
    gk.execute(lambda: ran.append("a"), service="default")
    gk.execute(lambda: ran.append("b"), service="default")  # queued
    assert gk.get_queue_status().depth == 1

    clock.t += 61.0  # per-minute window resets
    assert gk.drain() == 1
    assert ran == ["a", "b"]
    status = gk.get_queue_status()
    assert status.depth == 0 and status.drained_total == 1


def test_retries_stop_at_max_retries_then_raise(tmp_path: Path) -> None:
    """Sustained transient failures retry exactly ``max_retries`` times, then raise."""
    sleeps: list[float] = []
    clock = FakeClock()
    gk = make_gatekeeper(
        make_config(retry_after_seconds=1, max_retries=2),
        clock,
        tmp_path,
        run_id="run-retry",
        sleep_fn=sleeps.append,
    )

    def always_fail() -> None:
        raise ConnectionError("down")

    with pytest.raises(ConnectionError, match="down"):
        gk.execute(always_fail, service="default")

    assert sleeps == [1.0, 2.0]  # 2 retries, exponential backoff from config base 1
    retries = [e for e in read_jsonl(tmp_path / "run-retry.jsonl") if e["event_type"] == "retry"]
    assert len(retries) == 2


def test_backpressure_when_queue_full(tmp_path: Path) -> None:
    """At ``queue_max_depth`` an extra overflow raises ``QueueFullError`` (backpressure)."""
    clock = FakeClock()
    gk = make_gatekeeper(
        make_config(requests_per_minute=1, requests_per_hour=100, queue_max_depth=2),
        clock,
        tmp_path,
    )
    gk.execute(lambda: None, service="default")  # runs now
    gk.execute(lambda: None, service="default")  # queued 1
    gk.execute(lambda: None, service="default")  # queued 2 -> full
    assert gk.get_queue_status().depth == 2

    with pytest.raises(QueueFullError, match="default"):
        gk.execute(lambda: None, service="default")
    assert gk.get_queue_status().backpressure_total == 1


def test_concurrent_max_saturation_never_exceeds_cap(tmp_path: Path) -> None:
    """At the concurrency cap, an over-cap nested call enqueues; cap is never exceeded."""
    clock = FakeClock()
    gk = make_gatekeeper(make_config(concurrent_max=1, requests_per_minute=100), clock, tmp_path)
    peak = {"in_flight": 0}
    ran: list[str] = []

    def inner() -> None:
        ran.append("inner")

    def outer(gk: ApiGatekeeper = gk) -> None:
        ran.append("outer")
        peak["in_flight"] = max(peak["in_flight"], gk.get_queue_status().in_flight)
        assert gk.execute(inner, service="default") is None  # over cap -> queued

    gk.execute(outer, service="default")
    assert ran == ["outer"] and peak["in_flight"] == 1  # never exceeded cap of 1
    assert gk.drain() == 1 and ran == ["outer", "inner"]
