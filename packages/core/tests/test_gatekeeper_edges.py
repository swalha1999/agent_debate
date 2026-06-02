"""Consolidated Epic-13 §7 edge-case tests (TASKS.md 13.7, issue #96).

Sub-PRD ``docs/prds/api-gatekeeper.md`` §7 lists the edge cases the gatekeeper
must survive; this module asserts them **through the public API** as a final
acceptance pass:

* **sustained overflow + drain over multiple windows** — many queued calls
  released one window at a time, **FIFO order preserved** end-to-end (net-new:
  drain with depth>1 per window across several resets);
* **repeated transient failures up to ``max_retries``** with each retry **and**
  the terminal error logged;
* **concurrent-max saturation** combined with overflow drain;
* **config hot values out of range** — a ``ServiceLimits`` with ``0`` / negative
  values is rejected by validation (net-new: ``concurrent_max`` /
  ``queue_max_depth`` / ``retry_after_seconds`` direct-model validation, not just
  the loader's ``requests_per_minute`` case).

Determinism via injected ``time_fn``/``sleep_fn``; logs read from tmp JSONL.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from _gatekeeper_acceptance_helpers import FakeClock, make_config, make_gatekeeper, read_jsonl
from agent_debate.core.gatekeeper import ServiceLimits
from pydantic import ValidationError


def test_sustained_overflow_drains_fifo_over_many_windows(tmp_path: Path) -> None:
    """Many queued calls drain across windows in strict FIFO order (net-new edge)."""
    clock = FakeClock()
    gk = make_gatekeeper(make_config(requests_per_minute=1, requests_per_hour=100), clock, tmp_path)
    ran: list[str] = []

    gk.execute(lambda: ran.append("a"), service="default")  # runs now
    for name in ("b", "c", "d", "e"):
        gk.execute(lambda n=name: ran.append(n), service="default")  # all queued
    assert ran == ["a"] and gk.get_queue_status().depth == 4

    drained = 0
    while gk.get_queue_status().depth:
        clock.t += 61.0  # one more per-minute window opens room for exactly one
        drained += gk.drain()
    assert drained == 4
    assert ran == ["a", "b", "c", "d", "e"]  # FIFO preserved end-to-end (no reorder)


def test_repeated_transient_failures_log_each_retry_and_terminal_error(tmp_path: Path) -> None:
    """Every retry up to ``max_retries`` is logged, plus the final error outcome."""
    sleeps: list[float] = []
    clock = FakeClock()
    gk = make_gatekeeper(
        make_config(retry_after_seconds=2, max_retries=3),
        clock,
        tmp_path,
        run_id="run-edge-retry",
        sleep_fn=sleeps.append,
    )

    def always_timeout() -> None:
        raise TimeoutError("slow")

    with pytest.raises(TimeoutError):
        gk.execute(always_timeout, service="default")

    assert sleeps == [2.0, 4.0, 8.0]  # 3 retries, exponential backoff from config
    events = read_jsonl(tmp_path / "run-edge-retry" / "run-edge-retry.jsonl")
    assert len([e for e in events if e["event_type"] == "retry"]) == 3
    assert any(e["payload"].get("outcome") == "error" for e in events)


def test_concurrent_saturation_then_drain(tmp_path: Path) -> None:
    """Over-cap calls queue while saturated, then drain once the slot frees."""
    clock = FakeClock()
    gk = make_gatekeeper(make_config(concurrent_max=1, requests_per_minute=100), clock, tmp_path)
    ran: list[str] = []

    def nested() -> None:
        ran.append("nested")

    def holder() -> None:
        ran.append("holder")
        # Cap is 1 and holder holds it; two over-cap calls must both enqueue.
        assert gk.execute(nested, service="default") is None
        assert gk.execute(nested, service="default") is None

    gk.execute(holder, service="default")
    assert ran == ["holder"] and gk.get_queue_status().depth == 2
    assert gk.drain() == 2 and ran == ["holder", "nested", "nested"]


@pytest.mark.parametrize(
    "field",
    ["requests_per_minute", "requests_per_hour", "concurrent_max", "queue_max_depth"],
)
def test_config_zero_hot_value_rejected(field: str) -> None:
    """A ``0`` for any positive-only hot value is rejected (out-of-range config)."""
    payload = {
        "requests_per_minute": 30,
        "requests_per_hour": 500,
        "concurrent_max": 5,
        "retry_after_seconds": 30,
        "max_retries": 3,
        "queue_max_depth": 100,
    }
    payload[field] = 0
    with pytest.raises(ValidationError):
        ServiceLimits.model_validate(payload)


def test_config_negative_retry_after_rejected() -> None:
    """A negative ``retry_after_seconds`` is rejected (out-of-range config edge)."""
    with pytest.raises(ValidationError):
        ServiceLimits.model_validate(
            {
                "requests_per_minute": 30,
                "requests_per_hour": 500,
                "concurrent_max": 5,
                "retry_after_seconds": -1,
                "max_retries": 3,
                "queue_max_depth": 100,
            }
        )
