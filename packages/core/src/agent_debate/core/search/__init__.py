"""Pluggable search subpackage — the swappable web-search seam (Epic 3).

``docs/prds/search-plugin.md`` + PRD §5.5: web search is a MUST and a **plug-in**.
The engine and the ``web_search`` skill depend only on the stable interface
defined here; concrete vendors live behind it and are chosen by config
(``SEARCH_BACKEND``), so the search vendor is replaceable with one config change —
no engine/agent/skill edits.

Task 3.1 ships the *interface* (:class:`SearchResult`, :class:`SearchProvider`,
:data:`DEFAULT_MAX_RESULTS`); task 3.2 adds the **registry + factory**
(:func:`register_search_provider`, :func:`create_search_provider`,
:func:`available_search_backends`) that selects the active provider from
``SEARCH_BACKEND``. The default ``DuckDuckGoSearchProvider`` (task 3.3) registers
on top, and :class:`ResilientSearchProvider` (task 3.4) wraps any provider so a
flaky/failed search degrades to an empty list instead of crashing the debate
(sub-PRD §6). The re-exports below are the subpackage's public surface.
"""

from __future__ import annotations

from agent_debate.core.search.base import (
    DEFAULT_MAX_RESULTS,
    SearchProvider,
    SearchResult,
)
from agent_debate.core.search.duckduckgo import DuckDuckGoSearchProvider
from agent_debate.core.search.errors import UnknownSearchBackendError
from agent_debate.core.search.registry import (
    available_search_backends,
    create_search_provider,
    register_search_provider,
)
from agent_debate.core.search.resilient import ResilientSearchProvider
from agent_debate.core.search.tavily import TavilySearchProvider

__all__ = [
    "DEFAULT_MAX_RESULTS",
    "DuckDuckGoSearchProvider",
    "ResilientSearchProvider",
    "SearchProvider",
    "SearchResult",
    "TavilySearchProvider",
    "UnknownSearchBackendError",
    "available_search_backends",
    "create_search_provider",
    "register_search_provider",
]
