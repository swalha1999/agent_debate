"""Unit tests for :class:`TavilySearchProvider` — the swap-proof stub (task 3.5).

TDD red-first contract for the **second** search vendor of the pluggable-search
sub-PRD (``docs/prds/search-plugin.md`` §3/§4/§7, PRD §5.5): the acceptance
criterion is that *"switching backend is a one-line config change, proven with a
stub second provider."* This module is that proof.

The provider is a deliberate **stub** — it makes **no** network call and pulls in
**no** Tavily SDK. It exists to demonstrate that registering a second provider
plus flipping ``SEARCH_BACKEND`` is enough to swap vendors with **zero** engine /
factory / interface edits. The tests assert:

* the same :func:`create_search_provider` call returns *two different* provider
  types purely by changing ``SEARCH_BACKEND`` (``duckduckgo`` vs ``tavily``) — the
  core one-line-swap proof,
* the stub structurally satisfies the :class:`SearchProvider` protocol,
* its ``name`` is the single-source registry key ``"tavily"``,
* it reads its key from ``SEARCH_API_KEY`` (the constructed instance carries it),
* ``search`` returns a ``list[SearchResult]`` deterministically (no network),
* the stub signals clearly when used without a configured key.
"""

from __future__ import annotations

import pytest
from agent_debate.core import (
    SearchProvider,
    SearchResult,
    Settings,
    create_search_provider,
)
from agent_debate.core.search.duckduckgo import DuckDuckGoSearchProvider
from agent_debate.core.search.tavily import (
    TAVILY_BACKEND,
    TavilySearchProvider,
)


def test_one_line_swap_returns_tavily_provider() -> None:
    """``SEARCH_BACKEND=tavily`` resolves to the stub via the *same* factory."""
    provider = create_search_provider(Settings(search_backend="tavily", search_api_key="k"))

    assert isinstance(provider, TavilySearchProvider)


def test_swap_yields_two_provider_types_through_same_factory() -> None:
    """Flipping only ``SEARCH_BACKEND`` swaps the concrete provider type.

    This is the acceptance criterion: one config value, no engine/factory edits,
    two different vendors out of the identical :func:`create_search_provider` call.
    """
    duck = create_search_provider(Settings(search_backend="duckduckgo"))
    tav = create_search_provider(Settings(search_backend="tavily", search_api_key="k"))

    assert isinstance(duck, DuckDuckGoSearchProvider)
    assert isinstance(tav, TavilySearchProvider)
    assert type(duck).__name__ != type(tav).__name__


def test_satisfies_search_provider_protocol() -> None:
    """The stub structurally conforms to the ``SearchProvider`` protocol."""
    assert isinstance(TavilySearchProvider(api_key="k"), SearchProvider)


def test_provider_name_is_backend_key() -> None:
    """The stub's ``name`` is the single-source registry key ``"tavily"``."""
    assert TavilySearchProvider(api_key="k").name == TAVILY_BACKEND == "tavily"


def test_reads_key_from_settings() -> None:
    """The factory passes ``SEARCH_API_KEY`` into the stub's constructor."""
    provider = create_search_provider(
        Settings(search_backend="tavily", search_api_key="secret-key")
    )

    assert isinstance(provider, TavilySearchProvider)
    assert provider.api_key == "secret-key"


def test_search_returns_list_of_search_results() -> None:
    """``search`` returns a deterministic ``list[SearchResult]`` (no network)."""
    results = TavilySearchProvider(api_key="k").search("python")

    assert isinstance(results, list)
    assert results
    assert all(isinstance(r, SearchResult) for r in results)


def test_search_is_deterministic_for_a_query() -> None:
    """The stub is deterministic — same query, same canned results."""
    provider = TavilySearchProvider(api_key="k")

    assert provider.search("python") == provider.search("python")


def test_search_honours_max_results() -> None:
    """``max_results`` caps the number of stub results returned."""
    results = TavilySearchProvider(api_key="k").search("python", max_results=1)

    assert len(results) == 1


def test_missing_key_raises_clear_error_when_used() -> None:
    """A keyless stub fails loudly on ``search`` (key requirement enforced)."""
    provider = TavilySearchProvider(api_key=None)

    with pytest.raises(ValueError, match="SEARCH_API_KEY"):
        provider.search("python")
