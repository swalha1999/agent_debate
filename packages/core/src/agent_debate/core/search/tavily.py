"""Swap-proof second vendor — :class:`TavilySearchProvider` stub (task 3.5).

``docs/prds/search-plugin.md`` §3/§4/§7 + PRD §5.5: the seam's acceptance
criterion is *"switching backend is a one-line config change, proven with a stub
second provider."* This module is that proof. Registering this class plus setting
``SEARCH_BACKEND=tavily`` is **all** it takes to swap the active vendor — no
engine, agent, skill, factory, or interface edit. :func:`create_search_provider`
already resolves it purely by the config key and passes ``SEARCH_API_KEY`` to the
constructor (which exposes an ``api_key`` parameter, the registry's key seam).

This is intentionally a **stub**, not a live Tavily integration: it adds **no**
Tavily SDK dependency and makes **no** network call. :meth:`search` returns a
deterministic, clearly-marked canned :class:`SearchResult` list so the swap is
demonstrable end-to-end. The ``SEARCH_API_KEY`` requirement is still enforced —
:meth:`search` raises a clear error when no key is configured — mirroring the
shape a real keyed vendor would have. When a genuine Tavily integration is
wanted, replace :meth:`_fetch` with a live call routed through the API gatekeeper
(Epic 13); the registration, name, and key handling stay exactly as they are.
"""

from __future__ import annotations

from agent_debate.core.search.base import DEFAULT_MAX_RESULTS, SearchResult
from agent_debate.core.search.registry import register_search_provider

#: The registry key / provider name — single source, reused as ``name`` and as
#: the ``@register_search_provider`` key so the literal "tavily" lives once.
TAVILY_BACKEND = "tavily"

#: Marker baked into every stub result so it is never mistaken for a live hit.
_STUB_MARKER = "[stub] "

#: Deterministic canned hits the stub returns (proves the swap without network).
_STUB_RESULTS: tuple[tuple[str, str, str], ...] = (
    ("Tavily stub result one", "https://example.invalid/tavily/1", "Canned snippet one."),
    ("Tavily stub result two", "https://example.invalid/tavily/2", "Canned snippet two."),
    ("Tavily stub result three", "https://example.invalid/tavily/3", "Canned snippet three."),
)


@register_search_provider(TAVILY_BACKEND)
class TavilySearchProvider:
    """Stub Tavily backend proving the one-line vendor swap (sub-PRD §7).

    Conforms structurally to
    :class:`~agent_debate.core.search.base.SearchProvider`: it exposes
    :attr:`name` and :meth:`search`. The constructor takes ``api_key`` (fed
    ``SEARCH_API_KEY`` by :func:`create_search_provider`) and stores it; no
    network call happens in ``__init__``.

    Attributes:
        name: The registry key this provider is selected by (``"tavily"``).
        api_key: The configured ``SEARCH_API_KEY`` (``None`` when unset).
    """

    name = TAVILY_BACKEND

    def __init__(self, api_key: str | None = None) -> None:
        """Store the configured ``SEARCH_API_KEY`` (``None`` when unset)."""
        self.api_key = api_key

    def search(self, query: str, *, max_results: int = DEFAULT_MAX_RESULTS) -> list[SearchResult]:
        """Return up to ``max_results`` deterministic stub :class:`SearchResult`s.

        No network call is made — the results are canned and clearly marked as a
        stub. The ``SEARCH_API_KEY`` requirement is still enforced, matching the
        contract a real keyed vendor would impose.

        Args:
            query: The search query string (echoed into the stub titles).
            max_results: Maximum number of stub hits to return (default
                :data:`DEFAULT_MAX_RESULTS`).

        Returns:
            The canned results for ``query``, capped at ``max_results``.

        Raises:
            ValueError: If no ``SEARCH_API_KEY`` is configured — the stub mirrors
                a real keyed vendor by refusing to "search" without a key.
        """
        self._require_key()
        capped = _STUB_RESULTS[: max(0, max_results)]
        return [self._to_result(query, hit) for hit in capped]

    def _require_key(self) -> None:
        """Raise a clear error when ``SEARCH_API_KEY`` is missing (stub gate)."""
        if not self.api_key:
            raise ValueError(
                "TavilySearchProvider requires SEARCH_API_KEY to be set "
                "(stub — configure SEARCH_API_KEY or swap to a key-less backend)"
            )

    @staticmethod
    def _to_result(query: str, hit: tuple[str, str, str]) -> SearchResult:
        """Map one canned ``(title, url, snippet)`` tuple onto a result."""
        title, url, snippet = hit
        return SearchResult(
            title=f"{_STUB_MARKER}{title} for {query!r}",
            url=url,
            snippet=f"{_STUB_MARKER}{snippet}",
        )


__all__ = ["TAVILY_BACKEND", "TavilySearchProvider"]
