"""Placeholder scaffold tests for the root uv workspace (TASKS.md 0.1).

This is the first task in the repo — there are no packages yet. These are
intentionally minimal placeholder tests so ``uv run pytest`` is green from day
one (TDD scaffolding). The one real assertion locks the workspace contract: the
root ``pyproject.toml`` exists and declares a workspace over ``packages/*``.
Richer per-package tests arrive with their packages (tasks 0.2+).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"


def test_placeholder() -> None:
    """Trivial placeholder so the suite is green on a fresh scaffold."""
    assert True


def test_root_pyproject_declares_workspace() -> None:
    """Sanity check that the workspace root is wired up."""
    with PYPROJECT.open("rb") as handle:
        data = tomllib.load(handle)
    assert "packages/*" in data["tool"]["uv"]["workspace"]["members"]
