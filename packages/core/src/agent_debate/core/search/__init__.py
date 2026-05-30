"""Pluggable search subpackage — the swappable web-search seam (Epic 3).

``docs/prds/search-plugin.md`` + PRD §5.5: web search is a MUST and a **plug-in**.
The engine and the ``web_search`` skill depend only on the stable interface
defined here; concrete vendors live behind it and are chosen by config
(``SEARCH_BACKEND``), so the search vendor is replaceable with one config change —
no engine/agent/skill edits.

Task 3.1 ships the *interface* only (:class:`SearchResult`, :class:`SearchProvider`
and the :data:`DEFAULT_MAX_RESULTS` default). The provider registry (task 3.2) and
the default ``DuckDuckGoSearchProvider`` (task 3.3) build on this surface; the
re-exports below are the subpackage's public surface.
"""

from __future__ import annotations

from agent_debate.core.search.base import (
    DEFAULT_MAX_RESULTS,
    SearchProvider,
    SearchResult,
)

__all__ = ["DEFAULT_MAX_RESULTS", "SearchProvider", "SearchResult"]
