"""Default web-search vendor — :class:`DuckDuckGoSearchProvider` (task 3.3).

``docs/prds/search-plugin.md`` §4 + PRD §5.5: DuckDuckGo is the **default**
provider because it is free and needs **no API key**, so a fresh install with
``SEARCH_BACKEND=duckduckgo`` (the config default) returns clean
:class:`SearchResult`s out of the box. It is one concrete vendor behind the
stable :class:`~agent_debate.core.search.base.SearchProvider` seam — swapping to
another (e.g. a Tavily drop-in) stays a one-line config change.

The vendor library is ``ddgs`` (the maintained successor to
``duckduckgo-search``): ``DDGS().text(query, max_results=...)`` returns a list of
raw dicts with ``title`` / ``href`` / ``body`` keys, which :meth:`search` maps to
the uniform :class:`SearchResult` shape. Missing keys map to empty strings so a
sparse vendor payload never crashes the debate (sub-PRD §6).

Gatekeeper seam: the live ``DDGS().text(...)`` call below is the single external
hop. Task 13.6 wraps exactly this call in the API gatekeeper (Epic 13) for rate
limiting/retry; until then the mapping + registration are complete and the call
is isolated to :meth:`_fetch` so the wrapping is a one-spot change. Tests
monkeypatch :data:`DDGS`, so no test path touches the network.
"""

from __future__ import annotations

from typing import Any

from agent_debate.core.constants import DEFAULT_SEARCH_BACKEND
from agent_debate.core.search.base import DEFAULT_MAX_RESULTS, SearchResult
from agent_debate.core.search.registry import register_search_provider
from ddgs import DDGS

#: The registry key / provider name — single source, reused as ``name`` and as
#: the ``@register_search_provider`` key so the literal "duckduckgo" lives once.
DUCKDUCKGO_BACKEND = DEFAULT_SEARCH_BACKEND

#: ddgs raw-dict keys mapped onto the uniform :class:`SearchResult` fields.
_TITLE_KEY = "title"
_URL_KEY = "href"
_SNIPPET_KEY = "body"


@register_search_provider(DUCKDUCKGO_BACKEND)
class DuckDuckGoSearchProvider:
    """Free, key-less DuckDuckGo search backed by ``ddgs`` (sub-PRD §4).

    Conforms structurally to
    :class:`~agent_debate.core.search.base.SearchProvider`: it exposes
    :attr:`name` and :meth:`search`. Construction takes no arguments and makes no
    network call — only :meth:`search` reaches out.

    Attributes:
        name: The registry key this provider is selected by (``"duckduckgo"``).
    """

    name = DUCKDUCKGO_BACKEND

    def search(self, query: str, *, max_results: int = DEFAULT_MAX_RESULTS) -> list[SearchResult]:
        """Return up to ``max_results`` hits for ``query`` as :class:`SearchResult`s.

        Calls ``ddgs`` for raw dicts and maps each to the uniform result shape;
        raw dicts missing keys yield empty strings rather than raising, and an
        empty payload yields ``[]`` (sub-PRD §6 graceful handling).

        Args:
            query: The search query string.
            max_results: Maximum number of hits to request (default
                :data:`DEFAULT_MAX_RESULTS`).

        Returns:
            The mapped results, in vendor order.
        """
        raw = self._fetch(query, max_results=max_results)
        return [self._to_result(hit) for hit in raw]

    @staticmethod
    def _fetch(query: str, *, max_results: int) -> list[dict[str, Any]]:
        """Run the single external ``ddgs`` call (the API-gatekeeper seam, 13.6)."""
        return DDGS().text(query, max_results=max_results)

    @staticmethod
    def _to_result(hit: dict[str, Any]) -> SearchResult:
        """Map one ddgs raw dict onto a :class:`SearchResult` (missing -> "")."""
        return SearchResult(
            title=str(hit.get(_TITLE_KEY, "")),
            url=str(hit.get(_URL_KEY, "")),
            snippet=str(hit.get(_SNIPPET_KEY, "")),
        )


__all__ = ["DUCKDUCKGO_BACKEND", "DuckDuckGoSearchProvider"]
