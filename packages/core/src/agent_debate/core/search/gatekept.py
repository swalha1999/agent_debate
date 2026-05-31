"""Gatekeeper-routed search wrapper — no external call bypasses it (task 13.6).

``docs/prds/api-gatekeeper.md`` §1/§2/§6 and the search sub-PRD: **every** external
call (LLM *and* search) must pass through :meth:`ApiGatekeeper.execute`; "no bypass
exists (test-enforced)". The engine already routes model calls through the
gatekeeper (tasks 6.3/6.4). This module does the same for the **search** layer.

:class:`GatekeptSearchProvider` is a transparent decorator over any
:class:`~agent_debate.core.search.base.SearchProvider` — exactly analogous to
:class:`~agent_debate.core.search.resilient.ResilientSearchProvider`. It
implements the same protocol (``name`` + ``search``), so the registry/factory can
hand it back in place of the inner provider. On each :meth:`search` it routes the
inner provider's call through ``gatekeeper.execute(..., service="search")`` rather
than calling it directly, so the live external hop (e.g. DuckDuckGo's
``DDGS().text(...)``) is rate-limited, queued on overflow, retried and logged like
every other external call.

No values are hard-coded: the gatekeeper ``service`` selector is the named
:data:`~agent_debate.core.constants.SEARCH_SERVICE` constant (the gatekeeper reads
its limits from ``config/rate_limits.json`` and falls back to ``default`` when a
service is unconfigured). The decorator is purely a *routing* layer — it adds no
timeout/retry of its own (that is :class:`ResilientSearchProvider`'s job) and is
composed independently, so the two wrappers stack cleanly.
"""

from __future__ import annotations

from agent_debate.core.constants import SEARCH_SERVICE
from agent_debate.core.engine.gatekeeper_proto import Gatekeeper
from agent_debate.core.search.base import DEFAULT_MAX_RESULTS, SearchProvider, SearchResult


class GatekeptSearchProvider:
    """Route a :class:`SearchProvider`'s external call through the API gatekeeper.

    A transparent decorator implementing the :class:`SearchProvider` protocol
    (``name`` + ``search``): it delegates to ``inner`` but funnels the call through
    ``gatekeeper.execute(..., service="search")`` so the live external request is
    rate-limited/queued/retried/logged by the gatekeeper — never invoked directly.

    Args:
        inner: The wrapped concrete provider whose ``search`` performs the live call.
        gatekeeper: The API gatekeeper every external call routes through (Epic 13).

    Attributes:
        name: The wrapped provider's ``name`` (the decorator is transparent).
    """

    def __init__(self, inner: SearchProvider, *, gatekeeper: Gatekeeper) -> None:
        """Wrap ``inner`` so its external calls route through ``gatekeeper``."""
        self._inner = inner
        self._gatekeeper = gatekeeper
        #: The wrapped provider's registry name, surfaced transparently. A plain
        #: settable attribute (not a property) so the structural ``SearchProvider``
        #: protocol — which declares ``name`` settable — is satisfied exactly.
        self.name = inner.name

    def search(self, query: str, *, max_results: int = DEFAULT_MAX_RESULTS) -> list[SearchResult]:
        """Return the inner provider's hits, routed through the gatekeeper (§2).

        The inner ``search`` is handed to ``gatekeeper.execute`` with
        ``service="search"`` (never called directly), so the live external request
        is governed by the gatekeeper's rate limits, overflow queue, retry and
        logging — the same chokepoint every model call passes through.

        Args:
            query: The search query string.
            max_results: Maximum number of hits to request.

        Returns:
            The inner provider's results. ``[]`` is returned if the gatekeeper
            queued the call (overflow); the synchronous caller runs calls inline,
            so in practice the inner results flow straight back.
        """
        result = self._gatekeeper.execute(
            self._inner.search,
            query,
            max_results=max_results,
            service=SEARCH_SERVICE,
        )
        return result if result is not None else []


__all__ = ["GatekeptSearchProvider"]
