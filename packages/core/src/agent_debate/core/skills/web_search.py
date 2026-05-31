"""The ``web_search`` debate skill (TASKS.md 4.1, issue #32).

PRD §5.2 + ``docs/prds/search-plugin.md`` §5: a debater calls ``web_search`` to
fetch live evidence. Unlike the other Epic 4 skills (which are pure), this one
makes an **external** call, so it threads through *both* gatekeepers:

1. **Validate** the query at the trusted boundary via
   :func:`~agent_debate.core.security.validate_search_query` (7.2) — an abusive /
   oversized / control-char query is rejected before any network hop.
2. **Route** the active provider's call **through the API gatekeeper** (Epic 13,
   rate-limited) by building it with :func:`create_search_provider` and wrapping
   it in :class:`ResilientSearchProvider` so a flaky search degrades to ``[]``.
   Provider-agnostic — whatever ``SEARCH_BACKEND`` selects.
3. **Sanitise** every result **through the security gatekeeper**
   (:func:`~agent_debate.core.security.sanitize_search_result`, 7.5) *before*
   returning to the model — defending against prompt-injection in crawled text.
4. **Log** one ``tool_call`` event (run id, query, result count) via the LOG
   package for observability.

Full Pydantic AI tool *registration* (attaching to the agents) is task 4.5; here
we ship the tool-ready function plus its validated :class:`WebSearchInput` model,
re-exported from :mod:`agent_debate.core`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from agent_debate.core.constants import (
    WEB_SEARCH_DEFAULT_RUN_ID,
    WEB_SEARCH_EVENT_TYPE,
    WEB_SEARCH_TOOL,
)
from agent_debate.core.search.base import DEFAULT_MAX_RESULTS, SearchResult
from agent_debate.core.security import sanitize_search_result, validate_search_query
from agent_debate.core.settings import Settings
from agent_debate.core.skills._web_search_build import build_search_provider
from agent_debate.log import DEFAULT_RUNS_DIR, log_event

if TYPE_CHECKING:
    from agent_debate.core.engine.gatekeeper_proto import Gatekeeper


def web_search(
    query: str,
    *,
    settings: Settings | None = None,
    gatekeeper: Gatekeeper | None = None,
    max_results: int | None = None,
    run_id: str | None = None,
    runs_dir: Path | str = DEFAULT_RUNS_DIR,
) -> list[SearchResult]:
    """Search the web for ``query`` and return sanitised, prompt-safe results.

    The flow is: validate the query (7.2) → run the active provider through the
    API gatekeeper (Epic 13) with resilience → sanitise each result through the
    security gatekeeper (7.5) → log a ``tool_call`` event. A flaky / failed search
    returns ``[]`` rather than raising, so a debate never crashes from search.

    Args:
        query: The web-search query; rejected if blank / oversized / control-char.
        settings: Runtime settings selecting the backend + timeout; defaults to a
            fresh :class:`Settings` loaded from the environment.
        gatekeeper: The API gatekeeper every external call routes through. When
            ``None`` the provider runs ungatekept (e.g. an offline unit test).
        max_results: Maximum hits to request; defaults to
            :data:`DEFAULT_MAX_RESULTS` (config, not hard-coded).
        run_id: Run id for the ``tool_call`` log event; a module label is used
            when omitted.
        runs_dir: Directory holding the per-run JSONL sink.

    Returns:
        The sanitised :class:`SearchResult` list (possibly empty).

    Raises:
        InvalidInputError: If ``query`` fails trusted-boundary validation (7.2).
    """
    clean_query = validate_search_query(query)
    resolved_settings = settings if settings is not None else Settings()
    limit = max_results if max_results is not None else DEFAULT_MAX_RESULTS
    log_run_id = run_id if run_id is not None else WEB_SEARCH_DEFAULT_RUN_ID

    provider = build_search_provider(
        resolved_settings, gatekeeper=gatekeeper, run_id=log_run_id, runs_dir=runs_dir
    )
    raw = provider.search(clean_query, max_results=limit)
    results = [sanitize_search_result(hit, run_id=run_id, runs_dir=runs_dir) for hit in raw]
    _log_search(log_run_id, clean_query, len(results), runs_dir)
    return results


def _log_search(run_id: str, query: str, count: int, runs_dir: Path | str) -> None:
    """Emit one ``tool_call`` event recording the query and result count (§5.8)."""
    log_event(
        run_id=run_id,
        agent=WEB_SEARCH_TOOL,
        event_type=WEB_SEARCH_EVENT_TYPE,
        round=0,
        payload={"tool": WEB_SEARCH_TOOL, "query": query, "results": count},
        runs_dir=runs_dir,
    )


__all__ = ["web_search"]
