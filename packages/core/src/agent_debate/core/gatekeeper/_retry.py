"""Retry-with-backoff for transient gatekeeper failures (Epic 13, task 13.4).

Sub-PRD ``docs/prds/api-gatekeeper.md`` §1/§6/§7: a call that fails with a
**transient** error is retried up to ``max_retries`` times (from config), waiting
between attempts with a backoff derived purely from ``retry_after_seconds`` (also
from config). A **non-transient** error (e.g. a ``ValueError`` from bad input) is
not retried — it propagates immediately.

This module owns just the retry *policy* (which errors retry, how long to back
off, when to give up); the gatekeeper supplies the callable, the per-attempt
runner, the sleep seam and the retry-logging callback. No limit value is baked in
here: ``max_retries`` and ``retry_after_seconds`` arrive from
:class:`~agent_debate.core.gatekeeper.ServiceLimits`. The only literal is the
backoff base (a strategy constant, not a rate limit), kept as a named constant.

Backoff strategy: **exponential**, ``retry_after_seconds * _BACKOFF_BASE ** n``
for the ``n``-th (0-based) retry — so retry 1 waits ``retry_after_seconds``,
retry 2 waits twice that, and so on. ``retry_after_seconds`` is the sole base, so
the whole schedule scales with config.
"""

from __future__ import annotations

from collections.abc import Callable

#: Exception types treated as **transient** (worth retrying): network/availability
#: hiccups rather than caller errors. Timeouts and dropped connections are the
#: canonical retryable failures; everything else (e.g. ``ValueError``) is
#: permanent and propagates without a retry. A type tuple, not a limit value.
TRANSIENT_ERRORS: tuple[type[BaseException], ...] = (TimeoutError, ConnectionError)

#: Geometric growth factor for the exponential backoff schedule. A strategy
#: constant (the curve's shape), not a configurable rate limit — the *magnitude*
#: comes entirely from ``retry_after_seconds``.
_BACKOFF_BASE = 2.0


def is_transient(exc: BaseException) -> bool:
    """Return ``True`` when ``exc`` is a transient (retryable) failure."""
    return isinstance(exc, TRANSIENT_ERRORS)


def backoff_delay(retry_after_seconds: int, retry_index: int) -> float:
    """Seconds to wait before the ``retry_index``-th (0-based) retry attempt.

    Exponential: ``retry_after_seconds * _BACKOFF_BASE ** retry_index``. The base
    delay and growth both derive from config's ``retry_after_seconds`` (the only
    magnitude), so no delay value is hard-coded.
    """
    return float(retry_after_seconds) * (_BACKOFF_BASE**retry_index)


def run_with_retry[T](
    attempt: Callable[[], T],
    *,
    max_retries: int,
    retry_after_seconds: int,
    sleep_fn: Callable[[float], None],
    on_retry: Callable[[int, float, BaseException], None],
) -> T:
    """Run ``attempt`` once, retrying transient failures up to ``max_retries``.

    On a transient failure with retries remaining, ``on_retry`` is called with the
    1-based retry number, the backoff delay and the error, then ``sleep_fn`` waits
    that delay (the seam tests inject so no real time passes), then ``attempt``
    runs again. A non-transient error, or exhausting ``max_retries``, re-raises the
    error to the caller.

    Args:
        attempt: The (already-instrumented) single call to run; may raise.
        max_retries: Maximum *additional* attempts after the first (from config).
        retry_after_seconds: Backoff base in seconds (from config).
        sleep_fn: Injected sleep seam invoked with each backoff delay.
        on_retry: Callback logging each scheduled retry (number, delay, error).

    Returns:
        The result of the first successful ``attempt``.
    """
    retries = 0
    while True:
        try:
            return attempt()
        except BaseException as exc:  # noqa: BLE001 — re-raised unless transient.
            if retries >= max_retries or not is_transient(exc):
                raise
            delay = backoff_delay(retry_after_seconds, retries)
            retries += 1
            on_retry(retries, delay, exc)
            sleep_fn(delay)


__all__ = ["TRANSIENT_ERRORS", "backoff_delay", "is_transient", "run_with_retry"]
