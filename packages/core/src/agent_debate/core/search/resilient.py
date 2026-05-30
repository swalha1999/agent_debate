"""Resilient search wrapper — graceful degradation for flaky search (task 3.4).

``docs/prds/search-plugin.md`` §6 + PRD §5.5: web search is flaky, so a search
that times out or fails must **degrade gracefully** — a debate must never crash
because search did. :class:`ResilientSearchProvider` is a transparent decorator
around any :class:`~agent_debate.core.search.base.SearchProvider`: it implements
the same protocol, so the registry/factory can hand it back in place of the inner
provider.

Per call it (1) runs the inner ``search`` under a **timeout**
(:func:`~agent_debate.core.search.run_with_timeout`), (2) **retries** transient
failures (timeouts, connection errors) with exponential **backoff**, then (3) on
persistent failure returns ``[]`` — *never* raising — and logs the degradation.

Distinct from the API gatekeeper (Epic 13), which retries for the *rate/throughput*
concern: this is the search layer's own "never throw to the caller" guarantee. To
avoid duplicating backoff, it reuses the gatekeeper's retry policy
(:func:`run_with_retry`).

No values are hard-coded: ``max_retries`` + ``retry_after_seconds`` come from the
``search`` :class:`~agent_debate.core.gatekeeper.ServiceLimits` and ``timeout_s``
from config (e.g. ``Settings.turn_timeout_s``). ``sleep_fn`` is an injected seam so
tests assert backoff delays without real sleeping.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from agent_debate.core.gatekeeper import ServiceLimits
from agent_debate.core.gatekeeper._retry import run_with_retry
from agent_debate.core.search._resilient_log import _ResilientLog
from agent_debate.core.search._timeout import run_with_timeout
from agent_debate.core.search.base import DEFAULT_MAX_RESULTS, SearchProvider, SearchResult
from agent_debate.log import DEFAULT_RUNS_DIR

#: Type of the timeout seam: run a no-arg call, bounded by ``timeout_s`` seconds.
TimeoutRunner = Callable[[Callable[[], list[SearchResult]], float], list[SearchResult]]


def _default_timeout_runner(
    call: Callable[[], list[SearchResult]], timeout_s: float
) -> list[SearchResult]:
    """Default timeout seam: the thread-based :func:`run_with_timeout` helper."""
    return run_with_timeout(call, timeout_s=timeout_s)


class ResilientSearchProvider:
    """Wrap a :class:`SearchProvider` so flaky search degrades to ``[]`` (§6).

    Implements the :class:`SearchProvider` protocol (``name`` + ``search``) by
    delegating to ``inner`` under a timeout + retry/backoff, then falling back to
    an empty list (logged) on persistent failure — so the caller never sees an
    exception from search.

    Attributes:
        name: The wrapped provider's ``name`` (the decorator is transparent).
    """

    def __init__(
        self,
        inner: SearchProvider,
        *,
        limits: ServiceLimits,
        timeout_s: float,
        run_id: str,
        runs_dir: Path | str = DEFAULT_RUNS_DIR,
        sleep_fn: Callable[[float], None] = time.sleep,
        timeout_runner: TimeoutRunner = _default_timeout_runner,
    ) -> None:
        self._inner = inner
        self._limits = limits
        self._timeout_s = timeout_s
        self._sleep_fn = sleep_fn
        self._timeout_runner = timeout_runner
        self._log = _ResilientLog(run_id, runs_dir)

    @property
    def name(self) -> str:
        """The wrapped provider's registry name (transparent passthrough)."""
        return self._inner.name

    def search(self, query: str, *, max_results: int = DEFAULT_MAX_RESULTS) -> list[SearchResult]:
        """Return inner results, or ``[]`` on persistent failure (never raising).

        Retries transient failures (timeout/connection) up to ``max_retries`` with
        exponential backoff per ``retry_after_seconds`` (both from ``limits``); each
        inner call is bounded by ``timeout_s``. After retries are exhausted — or on
        any other failure — the failure is logged and an empty list is returned, so
        a flaky search never crashes the debate (§6).

        Args:
            query: The search query string.
            max_results: Maximum number of hits to request.

        Returns:
            The inner provider's results, or ``[]`` on persistent failure.
        """

        def _attempt() -> list[SearchResult]:
            return self._timeout_runner(
                lambda: self._inner.search(query, max_results=max_results),
                self._timeout_s,
            )

        try:
            return run_with_retry(
                _attempt,
                max_retries=self._limits.max_retries,
                retry_after_seconds=self._limits.retry_after_seconds,
                sleep_fn=self._sleep_fn,
                on_retry=lambda n, delay, exc: self._log.retry(self.name, n, delay, exc),
            )
        except BaseException as exc:  # noqa: BLE001 — graceful degradation: never raise.
            self._log.degraded(self.name, query, exc)
            return []


__all__ = ["ResilientSearchProvider", "TimeoutRunner"]
