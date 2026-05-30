"""Epic-3 acceptance tests — the pluggable-search story END-TO-END (issue #31).

This module is the Epic-3 acceptance pass (mirroring how 1.5 / 2.5 / 13.7
consolidated their epics). It exercises the sub-PRD §7 acceptance criteria
(``docs/prds/search-plugin.md``) *through the public* ``agent_debate.core`` /
``agent_debate.core.search`` API — composing the factory, the concrete vendor,
and the resilient wrapper into the single flow a debate actually runs, rather
than re-testing internals already covered in isolation by ``test_search_*`` /
``test_duckduckgo`` / ``test_tavily_stub`` (3.1–3.5):

#. **``SEARCH_BACKEND=duckduckgo`` returns clean ``SearchResult``s** — the
   configured vendor is built by the factory and maps raw ``ddgs`` dicts to the
   uniform shape (network mocked).
#. **One-line backend swap** — flipping only ``SEARCH_BACKEND`` (duckduckgo ↔
   tavily) returns a different vendor through the *same* factory call, no engine
   edit.
#. **Empty / error paths return ``[]`` without crashing** — proven through the
   resilient wrapper around the real factory provider, so search degrades
   gracefully into a debate.

``ddgs`` is always monkeypatched and the resilient limits come from the real
``config/rate_limits.json`` ``search`` service — so nothing is hard-coded and no
test touches the network.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from agent_debate.core import (
    DuckDuckGoSearchProvider,
    ResilientSearchProvider,
    SearchProvider,
    SearchResult,
    Settings,
    TavilySearchProvider,
    create_search_provider,
)
from agent_debate.core.gatekeeper import load_rate_limit_config

#: The sub-PRD §3 backend keys this acceptance pass swaps between.
_DUCKDUCKGO = "duckduckgo"
_TAVILY = "tavily"


class _StubDDGS:
    """Stand-in for ``ddgs.DDGS`` returning canned raw dicts (no network)."""

    raw: list[dict[str, Any]] = []

    def text(self, query: str, **_kwargs: Any) -> list[dict[str, Any]]:
        return type(self).raw


@pytest.fixture
def _patch_ddgs(monkeypatch: pytest.MonkeyPatch) -> type[_StubDDGS]:
    """Replace the real ``DDGS`` with :class:`_StubDDGS` (network mocked out)."""
    _StubDDGS.raw = [
        {"title": "Py", "href": "https://py.example", "body": "snip"},
    ]
    monkeypatch.setattr("agent_debate.core.search.duckduckgo.DDGS", _StubDDGS)
    return _StubDDGS


def _resilient(inner: SearchProvider, runs_dir: Path) -> ResilientSearchProvider:
    """Wrap ``inner`` with the *real* ``search`` limits from config (not hard-coded)."""
    limits = load_rate_limit_config().get_service_limits("search")
    return ResilientSearchProvider(
        inner,
        limits=limits,
        timeout_s=Settings().turn_timeout_s,
        run_id="run-acceptance",
        runs_dir=runs_dir,
        sleep_fn=lambda _d: None,
    )


# --- Acceptance 1: SEARCH_BACKEND=duckduckgo returns clean SearchResults ------


def test_duckduckgo_backend_returns_clean_results(_patch_ddgs: type[_StubDDGS]) -> None:
    """The configured default vendor maps raw ``ddgs`` dicts to clean results."""
    provider = create_search_provider(Settings(search_backend=_DUCKDUCKGO))

    results = provider.search("python")

    assert isinstance(provider, DuckDuckGoSearchProvider)
    assert results == [SearchResult(title="Py", url="https://py.example", snippet="snip")]
    assert all(isinstance(r, SearchResult) for r in results)


def test_factory_returns_the_configured_provider(_patch_ddgs: type[_StubDDGS]) -> None:
    """The registry hands back exactly the provider ``SEARCH_BACKEND`` names."""
    duck = create_search_provider(Settings(search_backend=_DUCKDUCKGO))
    tav = create_search_provider(Settings(search_backend=_TAVILY, search_api_key="k"))

    assert duck.name == _DUCKDUCKGO
    assert tav.name == _TAVILY


# --- Acceptance 2: one-line backend swap, no engine edit ----------------------


def test_one_line_swap_through_same_factory(_patch_ddgs: type[_StubDDGS]) -> None:
    """Flipping only ``SEARCH_BACKEND`` swaps the vendor via the identical call."""
    duck = create_search_provider(Settings(search_backend=_DUCKDUCKGO))
    tav = create_search_provider(Settings(search_backend=_TAVILY, search_api_key="k"))

    assert isinstance(duck, DuckDuckGoSearchProvider)
    assert isinstance(tav, TavilySearchProvider)
    assert type(duck).__name__ != type(tav).__name__


# --- Acceptance 3: empty / error paths return [] without crashing -------------


def test_empty_payload_returns_empty_through_factory(
    _patch_ddgs: type[_StubDDGS], tmp_path: Path
) -> None:
    """An empty vendor payload yields ``[]`` end-to-end (graceful empty)."""
    _StubDDGS.raw = []
    provider = _resilient(create_search_provider(Settings(search_backend=_DUCKDUCKGO)), tmp_path)

    assert provider.search("python") == []


def test_vendor_failure_degrades_to_empty_for_a_debate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A crashing vendor degrades to ``[]`` through the resilient layer — no escape.

    This is the net-new composition: the *factory* provider, wrapped by the
    resilient layer with the real ``search`` limits, never lets a search failure
    reach a debate (sub-PRD §6/§7).
    """

    class _Boom:
        def text(self, *_a: Any, **_k: Any) -> list[dict[str, Any]]:
            raise ConnectionError("vendor down")

    monkeypatch.setattr("agent_debate.core.search.duckduckgo.DDGS", _Boom)
    provider = _resilient(create_search_provider(Settings(search_backend=_DUCKDUCKGO)), tmp_path)

    assert provider.search("python") == []  # never raises into the debate


def test_resilient_wrapper_is_a_drop_in_search_provider(
    _patch_ddgs: type[_StubDDGS], tmp_path: Path
) -> None:
    """The wrapped factory provider is still a ``SearchProvider`` (transparent)."""
    provider = _resilient(create_search_provider(Settings(search_backend=_DUCKDUCKGO)), tmp_path)

    assert isinstance(provider, SearchProvider)
    assert provider.name == _DUCKDUCKGO
    assert provider.search("python") == [
        SearchResult(title="Py", url="https://py.example", snippet="snip")
    ]
