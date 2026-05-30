"""Contract tests for the root ``README.md`` (TASKS.md 0.12, guideline §2.1).

Guideline §2.1 requires the root ``README.md`` to act as a full user manual so a
new developer can install and run the project from this file alone. These tests
lock the structural invariants the manual must satisfy:

* a project summary (what the system is),
* a **System requirements** section,
* an **Install** / **Installation** section,
* a **Usage** / **Quickstart** section,
* a **Troubleshooting** section, and
* links into ``docs/`` (the PRD and the tasks document) so the README is the
  entry point into the rest of the documentation.

Heading checks are case-insensitive and tolerant of Markdown ``#`` prefixes so
the manual can be re-worded without breaking the contract — only the presence of
each required section and link is asserted.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"


def _text() -> str:
    return README.read_text(encoding="utf-8")


def _has_heading(text: str, *alternatives: str) -> bool:
    """True if a Markdown heading matching any alternative exists (case-insensitive)."""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        title = stripped.lstrip("#").strip().lower()
        if any(re.search(alt.lower(), title) for alt in alternatives):
            return True
    return False


def test_readme_exists() -> None:
    """A committed root ``README.md`` must exist."""
    assert README.is_file()


def test_readme_is_substantive() -> None:
    """The README is a real manual, not the one-line placeholder it replaced."""
    assert len(_text().splitlines()) > 30


def test_readme_has_project_summary() -> None:
    """The README names the project and what it does (debate + controller)."""
    text = _text().lower()
    assert "agent_debate" in text or "agent debate" in text
    assert "debate" in text and "controller" in text


def test_readme_has_system_requirements_section() -> None:
    """A System requirements section lists what is needed to run the project."""
    text = _text()
    assert _has_heading(text, "system requirements", "requirements", "prerequisites")
    assert "3.12" in text  # Python version floor (PRD §4)
    assert "uv" in text.lower()


def test_readme_has_install_section() -> None:
    """A step-by-step Install / Installation section exists."""
    text = _text()
    assert _has_heading(text, "install", "installation", "getting started")
    assert "uv sync" in text
    assert ".env.example" in text


def test_readme_has_usage_section() -> None:
    """A Usage / Quickstart section explains how to run the project."""
    assert _has_heading(_text(), "usage", "quickstart", "quick start", "running")


def test_readme_has_troubleshooting_section() -> None:
    """A Troubleshooting section covers common setup problems."""
    assert _has_heading(_text(), "troubleshooting")


def test_readme_links_to_core_docs() -> None:
    """The README links into ``docs/`` (the PRD and the tasks document)."""
    text = _text()
    assert "docs/PRD.md" in text
    assert "docs/TASKS.md" in text
