"""No-bypass enforcement — every external call routes through the gatekeeper (13.6).

``docs/prds/api-gatekeeper.md`` §2/§6: *"No direct API calls may bypass the
gatekeeper"* and *"no bypass exists (test-enforced)"*. Two external-call kinds
exist: LLM **model** calls and **search** provider calls. This module enforces
that both route through :meth:`ApiGatekeeper.execute`, by two complementary
checks:

* **Behavioral** — a spy gatekeeper proves the gatekept search provider invokes
  ``execute(service="search")`` on each ``search`` (the engine's model-call
  routing is proven in ``test_turn_timeout.py``; mirrored briefly here).
* **Structural** — a source grep over ``packages/*/src`` (comments and string
  literals stripped) asserts the only direct external-call constructs (``DDGS(``
  and Pydantic-AI ``.run_sync(`` / ``.run_async(``) live inside a named allowlist
  of approved gatekeeper-routed modules; a NEW direct call anywhere else fails
  this test, catching a future bypass.
"""

from __future__ import annotations

import io
import re
import tokenize
from pathlib import Path
from typing import Any

from agent_debate.core import SearchResult
from agent_debate.core.constants import LOOP_MODEL_SERVICE, SEARCH_SERVICE
from agent_debate.core.search import GatekeptSearchProvider

#: Repo root — ``packages/core/tests`` is three parents below it.
_REPO_ROOT = Path(__file__).resolve().parents[3]

#: The source trees scanned for direct external-call constructs.
_SRC_GLOB = "packages/*/src"

#: Direct external-call constructs that MUST be funnelled through the gatekeeper.
#: Each maps a human label to the regex that finds the raw construct in source.
#: ``DDGS(`` is the live search-vendor hop; ``.run_sync(`` / ``.run_async(`` are
#: Pydantic-AI ``Agent`` invocations executed inline rather than via the engine's
#: gatekeeper-routed seam (``turn.py`` passes ``agent.run_sync`` *by reference*
#: into ``execute`` — no parenthesised invocation — so it is not a direct call).
_EXTERNAL_CALL_PATTERNS: dict[str, re.Pattern[str]] = {
    "ddgs_text": re.compile(r"\bDDGS\s*\("),
    "agent_run_sync": re.compile(r"\.run_sync\s*\("),
    "agent_run_async": re.compile(r"\.run_async\s*\("),
}

#: Allowlist: files permitted to contain a direct construct because the call is
#: the *seam* the gatekeeper wraps (it is invoked via ``execute``, not directly).
#: A new direct call OUTSIDE this set fails ``test_no_external_call_bypasses``.
_ALLOWLISTED_FILES: frozenset[str] = frozenset(
    {
        "packages/core/src/agent_debate/core/search/duckduckgo.py",  # DDGS seam (_fetch)
    }
)


class _SpyGatekeeper:
    """Records every ``execute`` call's ``service`` and runs the call inline."""

    def __init__(self) -> None:
        self.services: list[str] = []

    def execute(self, api_call: Any, *args: Any, service: str = "default", **kwargs: Any) -> Any:
        self.services += [service]
        return api_call(*args, **kwargs)


class _InnerProvider:
    """A minimal inner provider whose search yields one canned result."""

    name = "inner"

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        return [SearchResult(title=query, url="https://x.invalid", snippet="s")]


def test_search_call_routes_through_gatekeeper() -> None:
    """Behavioral: the gatekept provider invokes execute(service="search")."""
    keeper = _SpyGatekeeper()
    provider = GatekeptSearchProvider(_InnerProvider(), gatekeeper=keeper)

    provider.search("topic")

    assert keeper.services == [SEARCH_SERVICE], "search must route via execute(service='search')"


def test_model_and_search_service_names_are_distinct_constants() -> None:
    """Both external-call kinds have a named (non-hard-coded) service selector."""
    assert LOOP_MODEL_SERVICE == "anthropic"
    assert SEARCH_SERVICE == "search"
    assert LOOP_MODEL_SERVICE != SEARCH_SERVICE


def _source_files() -> list[Path]:
    """All ``.py`` files under every ``packages/*/src`` tree (sorted, stable)."""
    files: list[Path] = []
    for src in sorted(_REPO_ROOT.glob(_SRC_GLOB)):
        files += sorted(src.rglob("*.py"))
    return files


def test_source_tree_was_actually_scanned() -> None:
    """Guard: the scan globbed real files (a silent empty scan would pass vacuously)."""
    files = _source_files()
    assert files, "expected source files under packages/*/src"
    rels = {f.relative_to(_REPO_ROOT).as_posix() for f in files}
    assert rels >= _ALLOWLISTED_FILES, "allowlisted files must exist in the scanned tree"


def _code_only(text: str) -> str:
    """Return ``text`` with comments and string-literal *contents* stripped.

    Tokenising and dropping ``COMMENT``/``STRING`` tokens means a construct named
    only in a docstring or comment (e.g. ``DDGS().text(...)`` prose) never counts
    as a direct external call — only real code does.
    """
    kept: list[str] = []
    tokens = tokenize.generate_tokens(io.StringIO(text).readline)
    for tok in tokens:
        if tok.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        kept += [tok.string]
    return " ".join(kept)


def test_no_external_call_bypasses_the_gatekeeper() -> None:
    """Structural: direct external-call constructs only appear in allowlisted files.

    Fails if a NEW direct ``DDGS(``/``.run_sync(``/``.run_async(`` appears outside
    the approved gatekeeper-routed seam files — catching a future bypass at CI time.
    Comments and string literals are stripped first, so only real code counts.
    """
    offenders: dict[str, list[str]] = {}
    for path in _source_files():
        rel = path.relative_to(_REPO_ROOT).as_posix()
        if rel in _ALLOWLISTED_FILES:
            continue
        code = _code_only(path.read_text(encoding="utf-8"))
        hits = [label for label, pat in _EXTERNAL_CALL_PATTERNS.items() if pat.search(code)]
        if hits:
            offenders[rel] = hits

    assert not offenders, (
        "direct external calls bypassing the gatekeeper found outside the allowlist: "
        f"{offenders}. Route them through ApiGatekeeper.execute or extend "
        "_ALLOWLISTED_FILES if the call is itself a gatekeeper-wrapped seam."
    )
