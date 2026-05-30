"""Unit tests for the ``agent_debate.core.search`` provider registry (task 3.2).

TDD red-first contract for the **pluggable search** sub-PRD
(``docs/prds/search-plugin.md`` §3, PRD §5.5): providers register under a name
and the *active* one is chosen by config (``SEARCH_BACKEND``), so swapping the
search vendor is a **one-line config change** — no factory edits.

This task ships the *registry mechanism* (no real vendor — DuckDuckGo is 3.3):

* :func:`register_search_provider` — a class decorator that records a
  ``SearchProvider`` implementation under its registry key.
* :func:`create_search_provider` — the factory that looks up
  ``settings.search_backend`` and instantiates the matching provider, passing
  ``settings.search_api_key`` to providers that accept one.
* :func:`available_search_backends` — the sorted registered names, used both by
  the factory's error message and by callers that want to enumerate options.

The factory must make **no network call**: it only constructs the provider.
"""

from __future__ import annotations

import pytest
from agent_debate.core import (
    DEFAULT_MAX_RESULTS,
    SearchProvider,
    SearchResult,
    Settings,
    UnknownSearchBackendError,
    available_search_backends,
    create_search_provider,
    register_search_provider,
)
from agent_debate.core.search import registry as registry_mod


@pytest.fixture(autouse=True)
def _isolate_registry() -> object:
    """Snapshot/restore the global registry so tests never leak providers."""
    saved = dict(registry_mod._REGISTRY)
    try:
        yield
    finally:
        registry_mod._REGISTRY.clear()
        registry_mod._REGISTRY.update(saved)


def _settings(backend: str, *, api_key: str | None = None) -> Settings:
    """Build a ``Settings`` directly, bypassing env/.env for hermetic tests."""
    return Settings(search_backend=backend, search_api_key=api_key)


@register_search_provider("dummy_a")
class _DummyA:
    """A keyless provider registered under ``dummy_a``."""

    name = "dummy_a"

    def search(self, query: str, *, max_results: int = DEFAULT_MAX_RESULTS) -> list[SearchResult]:
        return [SearchResult(title=query, url="https://a.x", snippet="a")]


@register_search_provider("dummy_b")
class _DummyB:
    """A provider that accepts the optional ``api_key`` (registered ``dummy_b``)."""

    name = "dummy_b"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    def search(self, query: str, *, max_results: int = DEFAULT_MAX_RESULTS) -> list[SearchResult]:
        return [SearchResult(title=query, url="https://b.x", snippet="b")]


def test_decorator_returns_class_unchanged() -> None:
    """``register_search_provider`` is transparent — it returns the class as-is."""
    assert _DummyA().name == "dummy_a"
    assert isinstance(_DummyA(), SearchProvider)


def test_backend_selects_registered_provider() -> None:
    """``SEARCH_BACKEND`` picks the matching provider instance from the registry."""
    provider = create_search_provider(_settings("dummy_a"))

    assert isinstance(provider, _DummyA)
    assert isinstance(provider, SearchProvider)


def test_one_line_swap_changes_active_provider() -> None:
    """Changing only ``SEARCH_BACKEND`` returns the other provider — a one-line swap."""
    assert isinstance(create_search_provider(_settings("dummy_a")), _DummyA)
    assert isinstance(create_search_provider(_settings("dummy_b")), _DummyB)


def test_api_key_is_passed_to_providers_that_accept_one() -> None:
    """A provider whose constructor takes ``api_key`` receives ``SEARCH_API_KEY``."""
    provider = create_search_provider(_settings("dummy_b", api_key="sek-123"))

    assert isinstance(provider, _DummyB)
    assert provider.api_key == "sek-123"


def test_keyless_provider_ignores_api_key() -> None:
    """A keyless constructor is still constructed even when a key is configured."""
    provider = create_search_provider(_settings("dummy_a", api_key="sek-123"))

    assert isinstance(provider, _DummyA)


def test_unknown_backend_raises_actionable_error() -> None:
    """An unregistered ``SEARCH_BACKEND`` raises, naming the available backends."""
    with pytest.raises(UnknownSearchBackendError) as excinfo:
        create_search_provider(_settings("does-not-exist"))

    message = str(excinfo.value)
    assert "does-not-exist" in message
    assert "dummy_a" in message and "dummy_b" in message


def test_registering_by_name_makes_it_selectable() -> None:
    """Registering a brand-new name makes it selectable with no factory edits."""

    @register_search_provider("dummy_c")
    class _DummyC:
        name = "dummy_c"

        def search(
            self, query: str, *, max_results: int = DEFAULT_MAX_RESULTS
        ) -> list[SearchResult]:
            return []

    assert "dummy_c" in available_search_backends()
    assert isinstance(create_search_provider(_settings("dummy_c")), _DummyC)


def test_available_backends_is_sorted_and_includes_registered() -> None:
    """``available_search_backends`` lists registered names in sorted order."""
    names = available_search_backends()

    assert names == sorted(names)
    assert "dummy_a" in names and "dummy_b" in names


def test_duplicate_registration_is_rejected() -> None:
    """Re-registering an existing name fails loudly instead of silently shadowing."""
    with pytest.raises(ValueError, match="dummy_a"):

        @register_search_provider("dummy_a")
        class _Clash:
            name = "dummy_a"

            def search(
                self, query: str, *, max_results: int = DEFAULT_MAX_RESULTS
            ) -> list[SearchResult]:
                return []
