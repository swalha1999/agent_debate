"""Sanitise a whole web-search result through the gatekeeper (PRD §5.7, Epic 7).

A :class:`~agent_debate.core.search.SearchResult` is *untrusted* text returned by
a web-search vendor (sub-PRD §5: results are "sanitised against prompt-injection
before being returned to the model"). Its human-readable fields — ``title`` and
``snippet`` — can each smuggle an injection payload, so both must pass through
:func:`~agent_debate.core.security.sanitiser.sanitize_untrusted_text` before the
result can re-enter a prompt. The ``url`` is structural identity, not prose fed to
the model, so it is left intact (an empty or mangled URL would harm provenance
without improving safety).

This is the typed composition seam: callers (the ``web_search`` skill, task 4.1)
sanitise an entire result object in one call instead of hand-threading each field,
and the result stays a frozen :class:`SearchResult` so it flows on unchanged.
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.core.search.base import SearchResult
from agent_debate.core.security.sanitiser import sanitize_untrusted_text

#: Source label stamped on the sanitiser's log events for search-result fields, so
#: a neutralisation in a crawled result is attributable in the run log (§5.8).
SEARCH_SOURCE = "web_search"


def sanitize_search_result(
    result: SearchResult,
    *,
    run_id: str | None = None,
    runs_dir: Path | str | None = None,
) -> SearchResult:
    """Return a copy of ``result`` with its untrusted text fields neutralised.

    ``title`` and ``snippet`` are passed through
    :func:`sanitize_untrusted_text` (normalise → injection-neutralise → length-cap)
    so neither can act as an instruction once it re-enters a prompt; ``url`` is left
    unchanged as structural provenance. When ``run_id`` is supplied, any
    neutralisation is logged via the LOG package (observability).

    Args:
        result: An untrusted search hit from any vendor.
        run_id: When set, neutralisation emits a ``system`` log event.
        runs_dir: Optional run-log directory passed through to the LOG package.

    Returns:
        A new frozen :class:`SearchResult` with sanitised ``title``/``snippet``.
    """
    return result.model_copy(
        update={
            "title": sanitize_untrusted_text(
                result.title, source=SEARCH_SOURCE, run_id=run_id, runs_dir=runs_dir
            ),
            "snippet": sanitize_untrusted_text(
                result.snippet, source=SEARCH_SOURCE, run_id=run_id, runs_dir=runs_dir
            ),
        }
    )


__all__ = ["SEARCH_SOURCE", "sanitize_search_result"]
