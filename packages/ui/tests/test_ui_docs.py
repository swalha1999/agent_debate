"""Documentation test for the UI doc (task 11.7, issue #79).

Guideline §10.2 requires the interface be *documented* so a reader understands
it WITHOUT running it. Real browser screenshots are not feasible in this
headless/CI environment, so the doc uses annotated ASCII layout diagrams plus a
UX walkthrough. This test is the pragmatic TDD red→green for a docs deliverable:
it asserts ``docs/UI.md`` exists, carries the required sections, and references
the *real* element ids / panels / verdict fields that live in ``index.html`` —
so the doc cannot silently drift from the actual implementation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

#: Repo root: this file is ``packages/ui/tests/`` → up three parents.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_UI_DOC = _REPO_ROOT / "docs" / "UI.md"
_INDEX_HTML = (
    _REPO_ROOT / "packages" / "ui" / "src" / "agent_debate" / "ui" / "static" / "index.html"
)

#: Required section headings (matched case-insensitively, substring).
_REQUIRED_HEADINGS = ("overview", "layout", "walkthrough", "config")

#: Real element ids from ``index.html`` the doc must reference, so the doc
#: stays tied to the actual DOM (not an invented mock-up).
_REQUIRED_IDS = (
    "topic",
    "start",
    "status",
    "transcript-pro",
    "transcript-con",
    "controller-actions",
    "system-log-list",
    "verdict",
    "new-debate",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    """Return the UI doc text, failing clearly if the doc is absent."""
    assert _UI_DOC.exists(), f"UI documentation missing: {_UI_DOC}"
    return _UI_DOC.read_text(encoding="utf-8")


def test_ui_doc_exists() -> None:
    """``docs/UI.md`` exists (the documentation deliverable)."""
    assert _UI_DOC.is_file()


def test_required_headings_present(doc_text: str) -> None:
    """The doc carries Overview / Layout / Walkthrough / Config sections."""
    lowered = doc_text.lower()
    for heading in _REQUIRED_HEADINGS:
        assert f"# {heading}" in lowered or heading in lowered, heading
        assert f"#{heading}" not in lowered or heading in lowered


def test_required_headings_are_markdown_headings(doc_text: str) -> None:
    """Each required section appears as an actual Markdown heading line."""
    headings = {
        line.lstrip("#").strip().lower()
        for line in doc_text.splitlines()
        if line.lstrip().startswith("#")
    }
    blob = " ".join(headings)
    for heading in _REQUIRED_HEADINGS:
        assert heading in blob, heading


def test_real_element_ids_referenced(doc_text: str) -> None:
    """The doc references real ids that actually exist in index.html."""
    index = _INDEX_HTML.read_text(encoding="utf-8")
    for element_id in _REQUIRED_IDS:
        assert f'id="{element_id}"' in index, f"stale id in test: {element_id}"
        assert element_id in doc_text, f"doc omits real id: {element_id}"


def test_three_panels_and_verdict_described(doc_text: str) -> None:
    """The three panels + verdict fields are described in the walkthrough."""
    lowered = doc_text.lower()
    for term in ("transcript", "moderator", "system log", "verdict"):
        assert term in lowered, term
    # Real verdict fields surfaced by app.js / the verdict view.
    for field in ("winner", "converged", "summary", "token"):
        assert field in lowered, field


def test_config_api_base_url_documented(doc_text: str) -> None:
    """The config-driven API base URL + run command are documented."""
    assert "API_BASE_URL" in doc_text
    assert "agent-debate-ui" in doc_text or "uvicorn" in doc_text
