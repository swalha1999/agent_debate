"""Smoke test for the analysis notebook (issue #98, task 14.2, PRD §9).

A stdlib-only check (no ``nbformat``/``nbclient`` dependency is added — those are
not workspace deps): the committed ``notebooks/analysis.ipynb`` must be valid
nbformat-4 JSON, carry the four §9 analysis sections, and ship with cleared
outputs so no run output (and no accidental secret) is committed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

_NOTEBOOK = Path(__file__).resolve().parents[3] / "notebooks" / "analysis.ipynb"
_REQUIRED_SECTIONS = (
    "Who-wins distribution",
    "Agree-vs-disagree rate",
    "Drift / nudge frequency per side",
    "Tokens & latency",
)


def _notebook() -> dict[str, Any]:
    """Load and JSON-parse the committed analysis notebook."""
    return cast(dict[str, Any], json.loads(_NOTEBOOK.read_text(encoding="utf-8")))


def _cells() -> list[dict[str, Any]]:
    """Return the notebook's cell list."""
    return cast(list[dict[str, Any]], _notebook()["cells"])


def test_notebook_is_valid_nbformat_json() -> None:
    """The notebook parses as JSON and declares nbformat 4 with cells."""
    nb = _notebook()
    assert nb["nbformat"] == 4
    assert isinstance(nb["cells"], list) and nb["cells"]


def test_notebook_has_four_analysis_sections() -> None:
    """Every PRD §9 analysis appears in a markdown heading."""
    markdown = "\n".join(
        "".join(cell["source"]) for cell in _cells() if cell["cell_type"] == "markdown"
    )
    for section in _REQUIRED_SECTIONS:
        assert section in markdown


def test_notebook_carries_no_text_outputs() -> None:
    """Only rendered chart images may be embedded — never text/stream output.

    Task 14.3 embeds the §9 charts (``image/png``) so the notebook *shows* them,
    which is fine. Text/stream outputs are still forbidden: they could carry a
    stray printed value or secret, so any committed output must be an image only.
    """
    for cell in _cells():
        if cell["cell_type"] != "code":
            continue
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            assert output.get("output_type") == "display_data"
            assert set(data) == {"image/png"}
