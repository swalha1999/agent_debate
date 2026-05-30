"""Unit tests for :class:`DuckDuckGoSearchProvider` (task 3.3).

TDD red-first contract for the **default search vendor** of the pluggable-search
sub-PRD (``docs/prds/search-plugin.md`` §4, PRD §5.5): DuckDuckGo is free and
needs no API key, so ``SEARCH_BACKEND=duckduckgo`` must yield clean
:class:`SearchResult`s out of the box.

The underlying ``ddgs`` client is **always monkeypatched** here — no test makes a
real network call. We patch :meth:`ddgs.DDGS.text` to return canned raw dicts
(``title`` / ``href`` / ``body``) and assert the provider:

* maps each raw dict to a :class:`SearchResult` with the right field mapping,
* passes ``max_results`` through to the client,
* tolerates raw dicts with missing keys (no crash),
* returns ``[]`` for an empty raw payload,
* is registered so ``create_search_provider(Settings(SEARCH_BACKEND="duckduckgo"))``
  hands back a :class:`DuckDuckGoSearchProvider`.
"""

from __future__ import annotations

from typing import Any

import pytest
from agent_debate.core import (
    DEFAULT_MAX_RESULTS,
    SearchProvider,
    SearchResult,
    Settings,
    create_search_provider,
)
from agent_debate.core.search.duckduckgo import (
    DUCKDUCKGO_BACKEND,
    DuckDuckGoSearchProvider,
)


class _SpyDDGS:
    """Stand-in for ``ddgs.DDGS`` that records calls and returns canned dicts."""

    #: Mutated per-test to drive the canned return payload.
    raw: list[dict[str, Any]] = []
    #: Records the ``(query, max_results)`` the provider asked for.
    calls: list[tuple[str, int]] = []

    def text(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        type(self).calls.append((query, kwargs.get("max_results", -1)))
        return type(self).raw


@pytest.fixture(autouse=True)
def _patch_ddgs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the real ``DDGS`` class with :class:`_SpyDDGS` (no network)."""
    _SpyDDGS.raw = []
    _SpyDDGS.calls = []
    monkeypatch.setattr("agent_debate.core.search.duckduckgo.DDGS", _SpyDDGS)


def _raw(title: str, href: str, body: str) -> dict[str, Any]:
    return {"title": title, "href": href, "body": body}


def test_maps_raw_dicts_to_search_results() -> None:
    """Each ddgs raw dict becomes a ``SearchResult`` with mapped fields."""
    _SpyDDGS.raw = [
        _raw("A", "https://a.example", "snip a"),
        _raw("B", "https://b.example", "snip b"),
    ]

    results = DuckDuckGoSearchProvider().search("python")

    assert results == [
        SearchResult(title="A", url="https://a.example", snippet="snip a"),
        SearchResult(title="B", url="https://b.example", snippet="snip b"),
    ]
    assert all(isinstance(r, SearchResult) for r in results)


def test_default_max_results_passed_through() -> None:
    """Absent an override, the provider asks ddgs for ``DEFAULT_MAX_RESULTS``."""
    DuckDuckGoSearchProvider().search("x")

    assert _SpyDDGS.calls == [("x", DEFAULT_MAX_RESULTS)]


def test_explicit_max_results_passed_through() -> None:
    """An explicit ``max_results`` is forwarded verbatim to the client."""
    DuckDuckGoSearchProvider().search("x", max_results=3)

    assert _SpyDDGS.calls == [("x", 3)]


def test_missing_keys_are_handled_gracefully() -> None:
    """Raw dicts missing keys map to empty strings instead of crashing."""
    _SpyDDGS.raw = [{"title": "only title"}, {}]

    results = DuckDuckGoSearchProvider().search("x")

    assert results == [
        SearchResult(title="only title", url="", snippet=""),
        SearchResult(title="", url="", snippet=""),
    ]


def test_empty_raw_yields_empty_list() -> None:
    """No raw hits -> an empty result list (graceful empty handling)."""
    _SpyDDGS.raw = []

    assert DuckDuckGoSearchProvider().search("x") == []


def test_provider_name_is_backend_key() -> None:
    """The provider's ``name`` is the single-source registry key."""
    assert DuckDuckGoSearchProvider().name == DUCKDUCKGO_BACKEND == "duckduckgo"


def test_satisfies_search_provider_protocol() -> None:
    """The provider structurally conforms to the ``SearchProvider`` protocol."""
    assert isinstance(DuckDuckGoSearchProvider(), SearchProvider)


def test_registered_as_default_backend() -> None:
    """``SEARCH_BACKEND=duckduckgo`` resolves to this provider via the factory."""
    provider = create_search_provider(Settings(search_backend="duckduckgo"))

    assert isinstance(provider, DuckDuckGoSearchProvider)
