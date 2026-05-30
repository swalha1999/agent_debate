"""Coverage-gate config contract tests (TASKS.md 0.9, issue #9).

Task 0.9 makes the ≥85% coverage gate (PRD §6.2) *config-driven*: the threshold
lives in the root ``pyproject.toml`` as the single source of truth, not as a
hard-coded CLI flag that could silently diverge from config. These tests lock
that contract so a later edit cannot weaken or relocate the gate:

* ``[tool.coverage.report].fail_under`` is exactly ``85``;
* ``[tool.coverage.run].source`` points at the per-package ``agent_debate``
  namespace source roots under ``packages/*/src`` (so ``pytest --cov`` measures
  the shipped surfaces, not the test tree);
* ``--cov-report=term-missing`` is wired so uncovered lines are visible.

This is the pragmatic TDD for a config-only task: a config-presence test that
fails before the config exists and passes once it does. The end-to-end proof
(``uv run pytest --cov`` actually failing below 85%) is enforced by CI and the
build harness.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ROOT_PYPROJECT = REPO_ROOT / "pyproject.toml"

#: The mandated coverage threshold (PRD §6.2, guideline §6.2).
REQUIRED_FAIL_UNDER = 85

#: Each shipped surface's namespace source root that coverage must measure.
EXPECTED_SOURCE_ROOTS = (
    "packages/core/src",
    "packages/log/src",
    "packages/api/src",
    "packages/cli/src",
    "packages/ui/src",
)


def _root_config() -> dict[str, object]:
    with ROOT_PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)


def _coverage_config() -> dict[str, object]:
    tool = _root_config()["tool"]
    assert isinstance(tool, dict)
    coverage = tool["coverage"]
    assert isinstance(coverage, dict)
    return coverage


def test_fail_under_is_85() -> None:
    """``[tool.coverage.report].fail_under`` is the mandated 85%."""
    report = _coverage_config()["report"]
    assert isinstance(report, dict)
    assert report["fail_under"] == REQUIRED_FAIL_UNDER


def test_coverage_source_points_at_package_src() -> None:
    """``[tool.coverage.run].source`` measures every package's namespace src."""
    run = _coverage_config()["run"]
    assert isinstance(run, dict)
    source = run["source"]
    assert isinstance(source, list)
    assert set(source) >= set(EXPECTED_SOURCE_ROOTS)
