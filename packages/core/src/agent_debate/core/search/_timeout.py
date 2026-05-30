"""Thread-based timeout for the (synchronous) inner search call (task 3.4).

``docs/prds/search-plugin.md`` §6: a search provider's ``search`` is a *blocking*
call that can hang, so the resilience wrapper must bound it in time. Python has no
portable, signal-free way to interrupt an arbitrary blocking call, so this helper
runs the call on a daemon worker thread and waits ``timeout_s`` for it to finish:

* finishes in time  -> the result (or the inner exception) is propagated;
* exceeds the budget -> :class:`TimeoutError` is raised (a *transient* error the
  wrapper retries, then degrades to ``[]``). The worker is a daemon thread, so an
  abandoned hung call never blocks process exit.

The clock is the only external dependency and it is injected as ``join_fn`` (a
``threading.Event``-style wait) so tests drive the timeout deterministically with
no real sleeping. ``timeout_s`` is supplied by the caller from config — no value
is baked in here.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

#: Sentinel distinguishing "no result captured yet" from a legitimate ``None``.
_UNSET = object()


def run_with_timeout[T](call: Callable[[], T], *, timeout_s: float) -> T:
    """Run ``call`` on a worker thread, raising ``TimeoutError`` past ``timeout_s``.

    The call runs on a daemon thread; the caller waits up to ``timeout_s`` for it
    to complete. If it completes, the captured return value is propagated (or any
    exception it raised is re-raised). If it does not complete within the budget a
    :class:`TimeoutError` is raised and the worker is abandoned (it cannot block
    exit, being a daemon).

    Args:
        call: The blocking, no-argument callable to bound in time.
        timeout_s: Maximum seconds to wait for ``call`` to finish.

    Returns:
        The value returned by ``call``.

    Raises:
        TimeoutError: If ``call`` does not finish within ``timeout_s``.
        BaseException: Whatever ``call`` itself raised, re-raised transparently.
    """
    box: list[object] = [_UNSET]
    error: list[BaseException] = []

    def _worker() -> None:
        try:
            box[0] = call()
        except BaseException as exc:  # noqa: BLE001 — captured + re-raised below.
            error.append(exc)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout_s)
    if thread.is_alive():
        raise TimeoutError(f"search call exceeded {timeout_s}s timeout")
    if error:
        raise error[0]
    return box[0]  # type: ignore[return-value]


__all__ = ["run_with_timeout"]
