"""Unit tests for the ``agent_debate.core.search`` provider interface (task 3.1).

TDD red-first contract for the **pluggable search** sub-PRD
(``docs/prds/search-plugin.md`` §2, PRD §5.5): a stable interface so the web
vendor is swappable with one config change. This task ships *only* the interface
(no concrete provider — DuckDuckGo is 3.3, the registry is 3.2):

* :class:`SearchResult` — a Pydantic ``BaseModel`` carrying ``title`` / ``url`` /
  ``snippet`` strings; it validates field types and round-trips through JSON.
* :class:`SearchProvider` — a runtime-checkable ``Protocol`` with a ``name``
  attribute and ``search(query, *, max_results=DEFAULT_MAX_RESULTS)`` returning a
  ``list[SearchResult]``. A class supplying both members satisfies it (and can be
  duck-typed); one missing either member does not.
"""

from __future__ import annotations

import pytest
from agent_debate.core import (
    DEFAULT_MAX_RESULTS,
    SearchProvider,
    SearchResult,
)
from pydantic import ValidationError


def test_search_result_holds_title_url_snippet() -> None:
    """A ``SearchResult`` exposes the three sub-PRD §2 string fields."""
    result = SearchResult(
        title="Pluggable search",
        url="https://example.com/search",
        snippet="A swappable web-search plug-in.",
    )

    assert result.title == "Pluggable search"
    assert result.url == "https://example.com/search"
    assert result.snippet == "A swappable web-search plug-in."


def test_search_result_round_trips_through_json() -> None:
    """``SearchResult`` serialises and reloads unchanged (JSON-safe contract)."""
    result = SearchResult(title="t", url="https://e.x", snippet="s")

    restored = SearchResult.model_validate_json(result.model_dump_json())

    assert restored == result


def test_search_result_rejects_non_string_fields() -> None:
    """Fields are typed ``str`` — a non-coercible value fails validation."""
    with pytest.raises(ValidationError):
        SearchResult(title=["not", "a", "string"], url="https://e.x", snippet="s")  # type: ignore[arg-type]


def test_default_max_results_is_five() -> None:
    """The interface default page size matches the sub-PRD §2 signature."""
    assert DEFAULT_MAX_RESULTS == 5


class _DummyProvider:
    """A minimal concrete provider satisfying the structural Protocol."""

    name = "dummy"

    def search(self, query: str, *, max_results: int = DEFAULT_MAX_RESULTS) -> list[SearchResult]:
        return [
            SearchResult(title=query, url="https://e.x", snippet="hit") for _ in range(max_results)
        ]


class _NotAProvider:
    """Missing both ``name`` and ``search`` — must not satisfy the Protocol."""


def test_concrete_provider_satisfies_protocol() -> None:
    """A class with ``name`` + ``search`` is a structural ``SearchProvider``."""
    provider: SearchProvider = _DummyProvider()

    assert isinstance(provider, SearchProvider)


def test_concrete_provider_is_duck_callable() -> None:
    """The provider's ``search`` honours the default and explicit page size."""
    provider = _DummyProvider()

    assert len(provider.search("q")) == DEFAULT_MAX_RESULTS
    explicit = provider.search("q", max_results=2)
    assert len(explicit) == 2
    assert all(isinstance(item, SearchResult) for item in explicit)


def test_incomplete_class_does_not_satisfy_protocol() -> None:
    """A class missing ``name``/``search`` is not a ``SearchProvider``."""
    assert not isinstance(_NotAProvider(), SearchProvider)
