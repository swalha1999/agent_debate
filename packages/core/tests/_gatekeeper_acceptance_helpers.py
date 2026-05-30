"""Shared fixtures/helpers for the Epic-13 gatekeeper acceptance pass (task 13.7).

The consolidated acceptance + edge tests (``test_gatekeeper_acceptance.py`` and
``test_gatekeeper_edges.py``) exercise the sub-PRD §6 acceptance criteria and §7
edge cases end-to-end **through the public** :class:`ApiGatekeeper` **API**. They
share one in-test config builder, a deterministic injectable clock and a JSONL
reader so every limit *value* provably comes from config (none hard-coded) and so
logged events are asserted from the tmp ``runs_dir`` sink the LOG package writes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_debate.core.gatekeeper import ApiGatekeeper, RateLimitConfig


class FakeClock:
    """A monotonic clock the tests advance explicitly (deterministic windows)."""

    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def make_config(
    *,
    requests_per_minute: int = 30,
    requests_per_hour: int = 500,
    concurrent_max: int = 5,
    retry_after_seconds: int = 30,
    max_retries: int = 3,
    queue_max_depth: int = 100,
) -> RateLimitConfig:
    """Build a one-service (``default``) config; every value is caller-supplied."""
    return RateLimitConfig.model_validate(
        {
            "version": "1.00",
            "services": {
                "default": {
                    "requests_per_minute": requests_per_minute,
                    "requests_per_hour": requests_per_hour,
                    "concurrent_max": concurrent_max,
                    "retry_after_seconds": retry_after_seconds,
                    "max_retries": max_retries,
                    "queue_max_depth": queue_max_depth,
                }
            },
        }
    )


def make_gatekeeper(
    config: RateLimitConfig,
    clock: FakeClock,
    tmp_path: Path,
    *,
    run_id: str = "run-acc",
    sleep_fn: Any = None,
) -> ApiGatekeeper:
    """Wire a gatekeeper to the injected clock + tmp JSONL sink (no real waits)."""
    if sleep_fn is None:
        return ApiGatekeeper(config, run_id=run_id, runs_dir=tmp_path, time_fn=clock)
    return ApiGatekeeper(config, run_id=run_id, runs_dir=tmp_path, time_fn=clock, sleep_fn=sleep_fn)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Parse every non-blank line of a JSONL file into a list of dicts."""
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
