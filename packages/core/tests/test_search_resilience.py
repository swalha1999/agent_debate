"""Unit tests for the resilient search wrapper (task 3.4, issue #29).

Sub-PRD ``docs/prds/search-plugin.md`` §6: search can be flaky, so a flaky/failed
search must **degrade gracefully** — a timeout or persistent failure returns an
empty list (never an exception) and is logged, so a debate never crashes from
search.

Written TDD-first (red before green). The :class:`ResilientSearchProvider` wraps
an inner ``SearchProvider`` (decorator pattern): it retries transient failures
with backoff, applies a timeout to each inner call, and on persistent failure
returns ``[]`` (logged). An injected ``sleep_fn`` captures the backoff delays so
tests never wait real seconds; the retry/failure events are asserted from the
JSONL the LOG package writes to a tmp ``runs_dir``. The retry/backoff *values*
come from the ``search`` service :class:`ServiceLimits` (``max_retries`` /
``retry_after_seconds``) and the timeout from ``Settings.turn_timeout_s`` — so
nothing is hard-coded.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_debate.core import SearchResult, Settings
from agent_debate.core.gatekeeper import ServiceLimits
from agent_debate.core.search.resilient import ResilientSearchProvider


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Parse every non-blank line of a JSONL file into a list of dicts.

    A run that logs nothing never creates the file, so a missing path means "no
    events" rather than an error.
    """
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _limits(*, retry_after_seconds: int = 2, max_retries: int = 2) -> ServiceLimits:
    """Build ``search``-shaped :class:`ServiceLimits` with the given retry knobs."""
    return ServiceLimits(
        requests_per_minute=20,
        requests_per_hour=300,
        concurrent_max=3,
        retry_after_seconds=retry_after_seconds,
        max_retries=max_retries,
        queue_max_depth=100,
    )


def _result(query: str) -> SearchResult:
    """One canned hit so tests can assert pass-through of real results."""
    return SearchResult(title=query, url="https://x.test", snippet="hit")


class _Inner:
    """A fake ``SearchProvider`` whose ``search`` is scripted per call."""

    name = "fake"

    def __init__(self, *, fail_times: int, exc: BaseException, results: list[SearchResult]) -> None:
        self._fail_times = fail_times
        self._exc = exc
        self._results = results
        self.calls = 0

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        self.calls += 1
        if self.calls <= self._fail_times:
            raise self._exc
        return self._results


def _wrap(
    inner: _Inner, *, limits: ServiceLimits, sleeps: list[float], runs_dir: Path
) -> ResilientSearchProvider:
    """Build a wrapper with the injected sleep seam + tmp run log."""
    return ResilientSearchProvider(
        inner,
        limits=limits,
        timeout_s=Settings().turn_timeout_s,
        run_id="run-search",
        runs_dir=runs_dir,
        sleep_fn=sleeps.append,
    )


def test_transient_failures_then_success_returns_results(tmp_path: Path) -> None:
    """N<max transient failures retry with backoff, then the results pass through."""
    sleeps: list[float] = []
    inner = _Inner(fail_times=2, exc=TimeoutError("slow"), results=[_result("q")])
    wrapper = _wrap(
        inner,
        limits=_limits(retry_after_seconds=2, max_retries=2),
        sleeps=sleeps,
        runs_dir=tmp_path,
    )

    assert wrapper.search("q") == [_result("q")]
    assert inner.calls == 3  # 2 failures + 1 success
    assert sleeps == [2.0, 4.0]  # exponential backoff from retry_after_seconds=2

    events = _read_jsonl(tmp_path / "run-search.jsonl")
    assert len([e for e in events if e["event_type"] == "retry"]) == 2


def test_persistent_failure_returns_empty_and_logs(tmp_path: Path) -> None:
    """Always-failing inner search returns ``[]`` (no exception) and logs the failure."""
    sleeps: list[float] = []
    inner = _Inner(fail_times=99, exc=ConnectionError("down"), results=[])
    wrapper = _wrap(
        inner,
        limits=_limits(retry_after_seconds=1, max_retries=2),
        sleeps=sleeps,
        runs_dir=tmp_path,
    )

    assert wrapper.search("q") == []  # graceful: never raises
    assert inner.calls == 3  # 1 initial + 2 retries
    assert sleeps == [1.0, 2.0]

    events = _read_jsonl(tmp_path / "run-search.jsonl")
    failures = [e for e in events if e["event_type"] == "timeout"]
    assert len(failures) == 1
    assert failures[0]["payload"]["error"] == "ConnectionError"


def test_timeout_returns_empty_and_logs(tmp_path: Path) -> None:
    """A timed-out inner call returns ``[]`` and logs the failure (never crashes)."""
    sleeps: list[float] = []
    inner = _Inner(fail_times=99, exc=TimeoutError("hung"), results=[])
    wrapper = _wrap(inner, limits=_limits(max_retries=0), sleeps=sleeps, runs_dir=tmp_path)

    assert wrapper.search("q") == []
    assert inner.calls == 1  # max_retries=0 -> no retries
    assert sleeps == []

    events = _read_jsonl(tmp_path / "run-search.jsonl")
    failures = [e for e in events if e["event_type"] == "timeout"]
    assert len(failures) == 1
    assert failures[0]["payload"]["error"] == "TimeoutError"


def test_empty_results_pass_through(tmp_path: Path) -> None:
    """Inner returning ``[]`` on success passes through as ``[]`` (no failure log)."""
    sleeps: list[float] = []
    inner = _Inner(fail_times=0, exc=TimeoutError("x"), results=[])
    wrapper = _wrap(inner, limits=_limits(), sleeps=sleeps, runs_dir=tmp_path)

    assert wrapper.search("q") == []
    assert inner.calls == 1
    assert sleeps == []

    events = _read_jsonl(tmp_path / "run-search.jsonl")
    assert not [e for e in events if e["event_type"] in {"retry", "timeout"}]


def test_real_timeout_is_caught_and_returns_empty(tmp_path: Path) -> None:
    """A genuinely slow inner call hits the timeout seam and degrades to ``[]``."""

    class _Hang:
        name = "hang"

        def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
            import time as _time

            _time.sleep(5)  # would exceed the tiny timeout below
            return [_result(query)]

    wrapper = ResilientSearchProvider(
        _Hang(),
        limits=_limits(max_retries=0),
        timeout_s=0,  # zero-second budget -> the call is treated as timed out
        run_id="run-hang",
        runs_dir=tmp_path,
        sleep_fn=lambda _d: None,
    )

    assert wrapper.search("q") == []
    events = _read_jsonl(tmp_path / "run-hang.jsonl")
    assert [e for e in events if e["event_type"] == "timeout"]


def test_wrapper_is_a_search_provider() -> None:
    """The wrapper is structurally a ``SearchProvider`` (transparent decorator)."""
    from agent_debate.core import SearchProvider

    inner = _Inner(fail_times=0, exc=TimeoutError("x"), results=[])
    wrapper = ResilientSearchProvider(
        inner,
        limits=_limits(),
        timeout_s=Settings().turn_timeout_s,
        run_id="r",
        runs_dir=Path("runs"),
        sleep_fn=lambda _d: None,
    )
    assert isinstance(wrapper, SearchProvider)
    assert wrapper.name == "fake"
