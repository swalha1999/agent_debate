"""Tests for the gatekeeper-routed search provider (task 13.6).

TDD red-first contract for ``docs/prds/api-gatekeeper.md`` §2/§6 and the search
sub-PRD's "every external request routes through the API gatekeeper": the live
provider call (e.g. DuckDuckGo's ``DDGS().text(...)``) must pass through
:meth:`ApiGatekeeper.execute` with ``service="search"`` — never directly.

:class:`GatekeptSearchProvider` is a transparent decorator (analogous to
:class:`ResilientSearchProvider`): it implements the ``SearchProvider`` protocol
and, on each :meth:`search`, routes the inner provider's call through an injected
gatekeeper. The factory wires it in by default so the active provider layer is
gatekeeper-routed (so the ``web_search`` skill, task 4.1, inherits it).

Everything runs offline: a spy gatekeeper records ``execute`` calls, and inner
providers return canned results (no network).
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
from agent_debate.core.constants import SEARCH_SERVICE
from agent_debate.core.search import GatekeptSearchProvider
from agent_debate.core.search import duckduckgo as ddg_mod


class _SpyGatekeeper:
    """A spy gatekeeper that records each ``execute`` call and runs it inline."""

    def __init__(self) -> None:
        self.services: list[str] = []
        self.calls = 0

    def execute(self, api_call: Any, *args: Any, service: str = "default", **kwargs: Any) -> Any:
        self.services += [service]
        self.calls += 1
        return api_call(*args, **kwargs)


class _RecordingProvider:
    """A keyless inner provider that records whether its search ran."""

    name = "recording"

    def __init__(self) -> None:
        self.queries: list[str] = []

    def search(self, query: str, *, max_results: int = DEFAULT_MAX_RESULTS) -> list[SearchResult]:
        self.queries += [query]
        return [SearchResult(title=query, url="https://x.invalid", snippet="s")]


def test_gatekept_provider_routes_search_through_execute() -> None:
    """The wrapper routes the inner search through ``execute(service="search")``."""
    keeper = _SpyGatekeeper()
    inner = _RecordingProvider()
    provider = GatekeptSearchProvider(inner, gatekeeper=keeper)

    results = provider.search("climate", max_results=3)

    assert keeper.calls == 1
    assert keeper.services == [SEARCH_SERVICE]
    assert inner.queries == ["climate"]  # the inner call actually ran (via the gate)
    assert results == [SearchResult(title="climate", url="https://x.invalid", snippet="s")]


def test_gatekept_provider_is_a_search_provider_and_transparent_name() -> None:
    """The wrapper satisfies the protocol and passes the inner ``name`` through."""
    provider = GatekeptSearchProvider(_RecordingProvider(), gatekeeper=_SpyGatekeeper())

    assert isinstance(provider, SearchProvider)
    assert provider.name == "recording"


def test_factory_wraps_active_provider_in_the_gatekeeper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``create_search_provider`` returns a gatekeeper-routed provider by default."""
    keeper = _SpyGatekeeper()
    provider = create_search_provider(Settings(search_backend="duckduckgo"), gatekeeper=keeper)

    assert isinstance(provider, GatekeptSearchProvider)
    # Stub the single external DDGS hop so exercising the provider stays offline,
    # then assert the live call routed through the gatekeeper (service="search").
    monkeypatch.setattr(
        ddg_mod.DuckDuckGoSearchProvider,
        "_fetch",
        staticmethod(lambda query, *, max_results: [{"title": query, "href": "u", "body": "b"}]),
    )
    provider.search("offline", max_results=1)
    assert keeper.services == [SEARCH_SERVICE]


def test_factory_without_gatekeeper_is_backward_compatible() -> None:
    """Omitting ``gatekeeper`` keeps the bare provider (no behaviour change)."""
    provider = create_search_provider(Settings(search_backend="duckduckgo"))

    assert not isinstance(provider, GatekeptSearchProvider)
    assert provider.name == "duckduckgo"
