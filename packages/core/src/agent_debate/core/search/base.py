"""Search provider interface — the swappable web-search seam (task 3.1).

``docs/prds/search-plugin.md`` §2 + PRD §5.5: web search is a **plug-in**, not
hardcoded. The engine and the ``web_search`` skill depend only on this stable
interface; concrete vendors (DuckDuckGo by default, task 3.3) live behind it and
are selected by config (``SEARCH_BACKEND``), so swapping the vendor is a one-line
config change with no engine/agent/skill edits.

This module ships *only* the interface:

* :class:`SearchResult` — the uniform Pydantic result shape every provider
  returns (``title`` / ``url`` / ``snippet``), so the ``web_search`` skill and the
  security gatekeeper sanitisation work identically regardless of vendor.
* :class:`SearchProvider` — the structural :class:`~typing.Protocol` a vendor must
  satisfy: a ``name`` and a ``search(query, *, max_results=…)`` method. It is
  ``runtime_checkable`` so the registry (task 3.2) can assert conformance.

:data:`DEFAULT_MAX_RESULTS` is the single source for the default page size that
appears in the :meth:`SearchProvider.search` signature.

No concrete provider, network call, or registry lives here. When a provider is
added (task 3.3) its actual ``search`` execution must route every external call
through the API gatekeeper (Epic 13) — this interface only fixes the contract.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

#: Default number of results a provider returns when the caller does not ask for
#: a specific count — the single source for the sub-PRD §2 signature default.
DEFAULT_MAX_RESULTS = 5


class SearchResult(BaseModel):
    """One web-search hit returned by any :class:`SearchProvider` (sub-PRD §2).

    The uniform contract shared by every vendor: the ``web_search`` skill and the
    gatekeeper sanitisation consume this same shape no matter which backend
    produced it. Frozen so a result cannot be mutated after a provider returns it
    (it flows on into sanitisation and the run log unchanged); ``extra="forbid"``
    rejects unexpected keys so a malformed provider payload fails loudly.

    Attributes:
        title: The result's display title.
        url: The result's source URL.
        snippet: A short extract/summary of the result.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    url: str
    snippet: str


@runtime_checkable
class SearchProvider(Protocol):
    """The structural contract a web-search vendor must satisfy (sub-PRD §2).

    A provider registers under :attr:`name` and exposes :meth:`search`; the active
    one is chosen by config (``SEARCH_BACKEND``). Being a ``runtime_checkable``
    :class:`~typing.Protocol`, conformance is purely structural — any object with a
    ``name`` and a matching ``search`` method qualifies (``isinstance`` works), so
    a new vendor is dropped in without subclassing anything upstream.

    Attributes:
        name: The registry key this provider is selected by (e.g. ``"duckduckgo"``).
    """

    name: str

    def search(self, query: str, *, max_results: int = DEFAULT_MAX_RESULTS) -> list[SearchResult]:
        """Return up to ``max_results`` hits for ``query`` as :class:`SearchResult`s.

        Implementations must route the underlying external request through the API
        gatekeeper (Epic 13) and surface results through the security gatekeeper;
        this signature only fixes the caller-facing contract.
        """
        ...


__all__ = ["DEFAULT_MAX_RESULTS", "SearchProvider", "SearchResult"]
