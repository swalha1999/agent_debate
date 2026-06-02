"""Unit tests for retry-with-backoff in ``ApiGatekeeper.execute`` (task 13.4).

Sub-PRD ``docs/prds/api-gatekeeper.md`` §1/§6/§7: transient failures are
**retried with backoff per config** (``max_retries``, ``retry_after_seconds``)
up to ``max_retries``; non-transient failures propagate immediately.

Written TDD-first (red before green). An injected ``sleep_fn`` captures the
backoff delays scheduled per retry (so tests never wait real seconds), and the
retry events are asserted from the JSONL the LOG package writes to a tmp
``runs_dir``. Limit *values* come from an in-test :class:`RateLimitConfig`, so
nothing is hard-coded.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from agent_debate.core.gatekeeper import ApiGatekeeper, RateLimitConfig


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Parse every non-blank line of a JSONL file into a list of dicts."""
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _config(*, retry_after_seconds: int = 30, max_retries: int = 3) -> RateLimitConfig:
    """Build a one-service (``default``) config with the given retry knobs."""
    return RateLimitConfig.model_validate(
        {
            "version": "1.00",
            "services": {
                "default": {
                    "requests_per_minute": 30,
                    "requests_per_hour": 500,
                    "concurrent_max": 5,
                    "retry_after_seconds": retry_after_seconds,
                    "max_retries": max_retries,
                    "queue_max_depth": 100,
                }
            },
        }
    )


class _Flaky:
    """A callable that raises ``exc`` its first ``fail_times`` calls, then returns."""

    def __init__(self, fail_times: int, exc: BaseException, result: Any = "ok") -> None:
        self.fail_times = fail_times
        self.exc = exc
        self.result = result
        self.calls = 0

    def __call__(self) -> Any:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise self.exc
        return self.result


def test_transient_failure_retried_then_succeeds(tmp_path: Path) -> None:
    """A transient error fewer than ``max_retries`` times eventually succeeds."""
    sleeps: list[float] = []
    gk = ApiGatekeeper(
        _config(retry_after_seconds=2, max_retries=3),
        run_id="run-retry",
        runs_dir=tmp_path,
        sleep_fn=sleeps.append,
    )
    flaky = _Flaky(2, TimeoutError("slow"), result=99)

    assert gk.execute(flaky, service="default") == 99
    assert flaky.calls == 3  # 2 failures + 1 success
    # Exponential backoff derived from retry_after_seconds=2: 2, then 4.
    assert sleeps == [2.0, 4.0]

    events = _read_jsonl(tmp_path / "run-retry" / "run-retry.jsonl")
    retries = [e for e in events if e["event_type"] == "retry"]
    assert len(retries) == 2
    assert all(e["payload"]["service"] == "default" for e in retries)


def test_retries_exhausted_reraises_last_error(tmp_path: Path) -> None:
    """More transient failures than ``max_retries`` re-raises after exhausting."""
    sleeps: list[float] = []
    gk = ApiGatekeeper(
        _config(retry_after_seconds=1, max_retries=2),
        run_id="run-exhaust",
        runs_dir=tmp_path,
        sleep_fn=sleeps.append,
    )
    flaky = _Flaky(99, ConnectionError("down"))

    with pytest.raises(ConnectionError, match="down"):
        gk.execute(flaky, service="default")

    # max_retries=2 -> 1 initial attempt + 2 retries = 3 calls, 2 backoff sleeps.
    assert flaky.calls == 3
    assert sleeps == [1.0, 2.0]

    events = _read_jsonl(tmp_path / "run-exhaust" / "run-exhaust.jsonl")
    assert len([e for e in events if e["event_type"] == "retry"]) == 2
    assert any(e["payload"].get("outcome") == "error" for e in events)


def test_non_transient_error_not_retried(tmp_path: Path) -> None:
    """A non-transient error (``ValueError``) propagates without any retry."""
    sleeps: list[float] = []
    gk = ApiGatekeeper(
        _config(max_retries=3),
        run_id="run-perm",
        runs_dir=tmp_path,
        sleep_fn=sleeps.append,
    )
    flaky = _Flaky(99, ValueError("bad input"))

    with pytest.raises(ValueError, match="bad input"):
        gk.execute(flaky, service="default")

    assert flaky.calls == 1  # no retries
    assert sleeps == []
    events = _read_jsonl(tmp_path / "run-perm" / "run-perm.jsonl")
    assert not [e for e in events if e["event_type"] == "retry"]


def test_zero_max_retries_does_not_retry(tmp_path: Path) -> None:
    """``max_retries=0`` runs the call exactly once even on a transient error."""
    sleeps: list[float] = []
    gk = ApiGatekeeper(
        _config(max_retries=0),
        run_id="run-zero",
        runs_dir=tmp_path,
        sleep_fn=sleeps.append,
    )
    flaky = _Flaky(99, TimeoutError("slow"))

    with pytest.raises(TimeoutError):
        gk.execute(flaky, service="default")
    assert flaky.calls == 1
    assert sleeps == []
