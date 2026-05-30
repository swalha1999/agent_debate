"""Unit tests for ``ApiGatekeeper.execute`` (TASKS.md 13.2, issue #91).

Epic 13 (``docs/prds/api-gatekeeper.md``) is the single chokepoint every
external LLM/search call passes through. Task 13.1 shipped the config surface;
this task ships the core :class:`ApiGatekeeper` whose :meth:`execute` runs a
passed callable, **checks rate limits before running it**, and **logs every
call** (service, latency, outcome) via the LOG package.

Written TDD-first (red before green). The tests use a tiny in-process fake
``api_call`` (no real network) and a :class:`RateLimitConfig` built from a temp
file, so the limit *values* demonstrably come from config, not code. Logged
events are asserted by reading the JSONL the LOG package writes to a tmp
``runs_dir``.

Scope note: the FIFO overflow queue (13.3), retry/concurrency refinements
(13.4) and the full ``get_queue_status`` (13.5) are later tasks; here a limit
*check* that raises :class:`RateLimitExceededError` when a window is exhausted is the
deliverable, plus a clean seam where overflow handling will hook.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from agent_debate.core.gatekeeper import (
    ApiGatekeeper,
    QueueStatus,
    RateLimitConfig,
    RateLimitExceededError,
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Parse every non-blank line of a JSONL file into a list of dicts."""
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _config(
    *,
    requests_per_minute: int = 30,
    requests_per_hour: int = 500,
    concurrent_max: int = 5,
) -> RateLimitConfig:
    """Build a one-service (``default``) config with the given limits."""
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
                }
            },
        }
    )


def test_execute_runs_callable_and_returns_result(tmp_path: Path) -> None:
    """``execute`` invokes the callable with args/kwargs and returns its value."""
    gk = ApiGatekeeper(_config(), run_id="run-x", runs_dir=tmp_path)

    def add(a: int, b: int = 0) -> int:
        return a + b

    assert gk.execute(add, 2, b=3, service="default") == 5


def test_successful_call_logs_service_latency_outcome(tmp_path: Path) -> None:
    """A success logs an event with service, latency_ms and outcome=success."""
    gk = ApiGatekeeper(_config(), run_id="run-ok", runs_dir=tmp_path)
    gk.execute(lambda: "ok", service="search")

    records = _read_jsonl(tmp_path / "run-ok.jsonl")
    assert len(records) == 1
    event = records[0]
    assert event["payload"]["service"] == "search"
    assert event["payload"]["outcome"] == "success"
    assert isinstance(event["latency_ms"], (int, float))
    assert event["latency_ms"] >= 0


def test_raising_call_logs_error_and_propagates(tmp_path: Path) -> None:
    """A raising callable logs outcome=error and re-raises the exception."""
    gk = ApiGatekeeper(_config(), run_id="run-err", runs_dir=tmp_path)

    def boom() -> None:
        raise ValueError("nope")

    with pytest.raises(ValueError, match="nope"):
        gk.execute(boom, service="default")

    records = _read_jsonl(tmp_path / "run-err.jsonl")
    assert len(records) == 1
    assert records[0]["payload"]["outcome"] == "error"
    assert records[0]["payload"]["service"] == "default"


def test_rate_limit_checked_before_execution(tmp_path: Path) -> None:
    """Exceeding requests_per_minute is caught *before* the callable runs."""
    gk = ApiGatekeeper(
        _config(requests_per_minute=1, requests_per_hour=100),
        run_id="run-rl",
        runs_dir=tmp_path,
    )
    calls: list[int] = []

    def record() -> int:
        calls.append(1)
        return len(calls)

    assert gk.execute(record, service="default") == 1
    with pytest.raises(RateLimitExceededError, match="default"):
        gk.execute(record, service="default")

    # The second callable never ran: the limit check blocked it pre-execution.
    assert calls == [1]


def test_rate_limit_uses_config_values_not_hardcoded(tmp_path: Path) -> None:
    """The per-minute threshold is read from config (custom value honoured)."""
    gk = ApiGatekeeper(
        _config(requests_per_minute=3, requests_per_hour=100),
        run_id="run-cfg",
        runs_dir=tmp_path,
    )
    for _ in range(3):
        gk.execute(lambda: None, service="default")
    with pytest.raises(RateLimitExceededError):
        gk.execute(lambda: None, service="default")


def test_unconfigured_service_falls_back_to_default(tmp_path: Path) -> None:
    """A service with no explicit entry uses the ``default`` limits."""
    gk = ApiGatekeeper(_config(), run_id="run-fb", runs_dir=tmp_path)
    assert gk.execute(lambda: 42, service="brand-new") == 42


def test_get_queue_status_returns_queue_status(tmp_path: Path) -> None:
    """``get_queue_status`` returns a ``QueueStatus`` (depth 0 in 13.2)."""
    gk = ApiGatekeeper(_config(), run_id="run-q", runs_dir=tmp_path)
    status = gk.get_queue_status()
    assert isinstance(status, QueueStatus)
    assert status.depth == 0
