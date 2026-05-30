"""Unit tests for the FIFO overflow queue (TASKS.md 13.3, issue #92).

Sub-PRD ``docs/prds/api-gatekeeper.md`` §5: when a rate limit is hit a request
is **enqueued** (FIFO, bounded ``queue_max_depth`` from config) instead of being
dropped or crashing; a genuinely **full** queue signals **backpressure**; queued
requests **drain** as the rate windows reset.

Written TDD-first (red before green). An injected fake clock (``time_fn``) makes
"a window has reset" deterministic: the test advances time, then drains. Limit
*values* and the queue depth come from a :class:`RateLimitConfig` built in-test,
so nothing is hard-coded.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from agent_debate.core.gatekeeper import (
    ApiGatekeeper,
    QueueFullError,
    RateLimitConfig,
    RateLimitExceededError,
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
                    "concurrent_max": 5,
                    "retry_after_seconds": 30,
                    "max_retries": 3,
                    "queue_max_depth": queue_max_depth,
                }
            },
        }
    )


def _gatekeeper(config: RateLimitConfig, clock: _FakeClock, tmp_path: Path) -> ApiGatekeeper:
    """Build a gatekeeper wired to an injectable clock + tmp log sink."""
    return ApiGatekeeper(config, run_id="run-q", runs_dir=tmp_path, time_fn=clock)


def test_limit_hit_enqueues_instead_of_raising(tmp_path: Path) -> None:
    """When the per-minute window is exhausted, an extra call is enqueued."""
    clock = _FakeClock()
    gk = _gatekeeper(_config(requests_per_minute=1, requests_per_hour=100), clock, tmp_path)

    assert gk.execute(lambda: "first", service="default") == "first"
    # The window is now full; this must NOT raise — it enqueues.
    result = gk.execute(lambda: "queued", service="default")
    assert result is None  # deferred: ran later via drain, not now

    status = gk.get_queue_status()
    assert status.depth == 1
    assert status.enqueued_total == 1


def test_advancing_clock_and_drain_runs_queued_call(tmp_path: Path) -> None:
    """After the window resets, ``drain`` runs the queued call in FIFO order."""
    clock = _FakeClock()
    gk = _gatekeeper(_config(requests_per_minute=1, requests_per_hour=100), clock, tmp_path)
    ran: list[str] = []

    gk.execute(lambda: ran.append("a"), service="default")
    gk.execute(lambda: ran.append("b"), service="default")  # enqueued
    assert ran == ["a"]
    assert gk.get_queue_status().depth == 1

    clock.t += 61.0  # per-minute window resets
    drained = gk.drain()
    assert drained == 1
    assert ran == ["a", "b"]
    status = gk.get_queue_status()
    assert status.depth == 0
    assert status.drained_total == 1


def test_fifo_order_preserved_on_drain(tmp_path: Path) -> None:
    """Queued calls drain in first-in-first-out order across resets.

    With ``requests_per_minute=1`` each window reset releases exactly one queued
    call; advancing the clock minute-by-minute drains b, then c, then d — proving
    arrival order is preserved (never c before b).
    """
    clock = _FakeClock()
    gk = _gatekeeper(_config(requests_per_minute=1, requests_per_hour=100), clock, tmp_path)
    ran: list[str] = []

    gk.execute(lambda: ran.append("a"), service="default")  # runs now
    for name in ("b", "c", "d"):
        gk.execute(lambda n=name: ran.append(n), service="default")  # enqueued
    assert ran == ["a"]
    assert gk.get_queue_status().depth == 3

    for expected in (["a", "b"], ["a", "b", "c"], ["a", "b", "c", "d"]):
        clock.t += 61.0  # next per-minute window opens room for one more
        assert gk.drain() == 1
        assert ran == expected
    assert gk.get_queue_status().depth == 0


def test_full_queue_signals_backpressure(tmp_path: Path) -> None:
    """Filling the queue to ``queue_max_depth`` then one more raises QueueFullError."""
    clock = _FakeClock()
    gk = _gatekeeper(
        _config(requests_per_minute=1, requests_per_hour=100, queue_max_depth=2),
        clock,
        tmp_path,
    )

    gk.execute(lambda: None, service="default")  # runs now
    gk.execute(lambda: None, service="default")  # enqueue 1
    gk.execute(lambda: None, service="default")  # enqueue 2 (queue full)
    assert gk.get_queue_status().depth == 2

    with pytest.raises(QueueFullError, match="default"):
        gk.execute(lambda: None, service="default")  # backpressure


def test_queue_max_depth_reported_from_config(tmp_path: Path) -> None:
    """``get_queue_status`` reports ``max_depth`` from config, not a literal."""
    clock = _FakeClock()
    gk = _gatekeeper(_config(queue_max_depth=7), clock, tmp_path)
    assert gk.get_queue_status().max_depth == 7


def test_enqueue_is_logged(tmp_path: Path) -> None:
    """An enqueue emits a log event so queue pressure is observable."""
    import json

    clock = _FakeClock()
    gk = _gatekeeper(_config(requests_per_minute=1, requests_per_hour=100), clock, tmp_path)
    gk.execute(lambda: "a", service="default")
    gk.execute(lambda: "b", service="default")  # enqueued -> logged

    lines = [
        json.loads(line)
        for line in (tmp_path / "run-q.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    enqueue_events = [e for e in lines if e["payload"].get("queue_event") == "enqueue"]
    assert len(enqueue_events) == 1
    assert enqueue_events[0]["payload"]["service"] == "default"


def test_error_types_carry_context() -> None:
    """The gatekeeper error types expose their service/window/depth context."""
    full = QueueFullError("anthropic", 5)
    assert full.service == "anthropic"
    assert full.max_depth == 5
    assert "anthropic" in str(full)

    limit = RateLimitExceededError("search", "requests_per_minute")
    assert limit.service == "search"
    assert limit.window == "requests_per_minute"
    assert "search" in str(limit)
