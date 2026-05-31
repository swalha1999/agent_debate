"""Structural type for the API gatekeeper the loop routes calls through (#48).

Orchestration sub-PRD §3.2 / §4 and ``docs/prds/api-gatekeeper.md`` §3: EVERY
external model call the debate loop makes must pass through the API gatekeeper's
:meth:`execute`. The loop depends only on that *shape*, not the concrete
:class:`~agent_debate.core.gatekeeper.ApiGatekeeper`, so tests can inject a spy /
fake that records each routed call. This :class:`~typing.Protocol` captures the
minimal surface the loop relies on (the real gatekeeper satisfies it structurally).

No external call is made here — this is a typing-only seam — so the gatekeeper
itself (Epic 13) is what the loop *uses*; this module just names its contract.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, TypeVar

_T = TypeVar("_T")


class Gatekeeper(Protocol):
    """Minimal :meth:`execute` surface the debate loop routes model calls through.

    Mirrors :meth:`~agent_debate.core.gatekeeper.ApiGatekeeper.execute`: run
    ``api_call`` (within rate limits, logging it) and return its result, selecting
    rate limits by ``service``. A real gatekeeper may return ``None`` when a call
    is queued; the synchronous loop runs calls immediately, so a result is returned.
    """

    def execute(
        self,
        api_call: Callable[..., _T],
        *args: Any,
        service: str = ...,
        **kwargs: Any,
    ) -> _T | None:
        """Run ``api_call`` through the gatekeeper, returning its result."""
        ...


__all__ = ["Gatekeeper"]
