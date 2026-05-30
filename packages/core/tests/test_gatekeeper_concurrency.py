"""Unit tests for the concurrency cap in ``ApiGatekeeper.execute`` (task 13.4).

Sub-PRD ``docs/prds/api-gatekeeper.md`` §4/§7: no more than ``concurrent_max``
calls (from config) may be **in flight** simultaneously for a service; a call
made while the service is saturated is **enqueued** (reusing the FIFO overflow
queue / backpressure path) rather than exceeding the cap.

Written TDD-first (red before green). Concurrency is exercised deterministically
in a single thread: the wrapped callable re-enters ``execute`` while it is itself
in flight, so the in-flight counter is provably at the cap when the nested call
is admitted-or-enqueued. The cap value comes from an in-test
:class:`RateLimitConfig`, so nothing is hard-coded.
"""

from __future__ import annotations

import contextlib
from pathlib import Path

from agent_debate.core.gatekeeper import ApiGatekeeper, RateLimitConfig


def _config(*, concurrent_max: int = 5) -> RateLimitConfig:
    """Build a one-service (``default``) config with the given concurrency cap."""
    return RateLimitConfig.model_validate(
        {
            "version": "1.00",
            "services": {
                "default": {
                    "requests_per_minute": 100,
                    "requests_per_hour": 1000,
                    "concurrent_max": concurrent_max,
                    "retry_after_seconds": 30,
                    "max_retries": 3,
                    "queue_max_depth": 100,
                }
            },
        }
    )


def test_concurrent_max_one_enqueues_nested_call(tmp_path: Path) -> None:
    """With ``concurrent_max=1``, a call started mid-flight is enqueued, not run."""
    gk = ApiGatekeeper(_config(concurrent_max=1), run_id="run-c1", runs_dir=tmp_path)
    ran: list[str] = []

    def inner() -> str:
        ran.append("inner")
        return "inner"

    def outer() -> str:
        ran.append("outer")
        # One call (outer) is already in flight; the cap is 1, so this nested
        # call must be enqueued (returns None) rather than exceeding the cap.
        assert gk.execute(inner, service="default") is None
        return "outer"

    assert gk.execute(outer, service="default") == "outer"
    # inner was deferred, not run, while outer held the only in-flight slot.
    assert ran == ["outer"]
    assert gk.get_queue_status().depth == 1

    # Once outer finished its slot freed; draining runs the queued inner call.
    assert gk.drain() == 1
    assert ran == ["outer", "inner"]


def test_inflight_released_after_call_completes(tmp_path: Path) -> None:
    """The in-flight slot is freed after each call so later calls run normally."""
    gk = ApiGatekeeper(_config(concurrent_max=1), run_id="run-rel", runs_dir=tmp_path)
    assert gk.execute(lambda: "a", service="default") == "a"
    # The slot from the first call was released, so a second call still runs now.
    assert gk.execute(lambda: "b", service="default") == "b"
    assert gk.get_queue_status().depth == 0


def test_inflight_released_even_when_call_raises(tmp_path: Path) -> None:
    """A raising call still releases its in-flight slot (no permanent leak)."""
    gk = ApiGatekeeper(_config(concurrent_max=1), run_id="run-raise", runs_dir=tmp_path)

    def boom() -> None:
        raise ValueError("nope")

    with contextlib.suppress(ValueError):
        gk.execute(boom, service="default")
    # Slot released despite the exception: a following call is admitted, not queued.
    assert gk.execute(lambda: "ok", service="default") == "ok"
    assert gk.get_queue_status().depth == 0


def test_cap_honored_across_capacity(tmp_path: Path) -> None:
    """At ``concurrent_max=2`` the third nested call is enqueued, the second runs."""
    gk = ApiGatekeeper(_config(concurrent_max=2), run_id="run-c2", runs_dir=tmp_path)
    ran: list[str] = []

    def third() -> str:
        ran.append("third")
        return "third"

    def second() -> str:
        ran.append("second")
        # Two now in flight (first + second) == cap; third is enqueued.
        assert gk.execute(third, service="default") is None
        return "second"

    def first() -> str:
        ran.append("first")
        # One in flight (first); second is under the cap of 2 and runs now.
        assert gk.execute(second, service="default") == "second"
        return "first"

    assert gk.execute(first, service="default") == "first"
    assert ran == ["first", "second"]
    assert gk.get_queue_status().depth == 1
