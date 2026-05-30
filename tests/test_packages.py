"""Skeleton tests for the five workspace packages (TASKS.md 0.2).

The repo ships five surfaces (PRD §5.1): ``core`` (SDK), ``log`` (logging),
and the ``api`` / ``cli`` / ``ui`` surfaces. This task only creates the empty
skeletons; later tasks fill them in. These tests lock two contracts:

1. Each ``agent_debate_<pkg>`` package imports cleanly.
2. Each package declares itself as a workspace member with the right name.
"""

from __future__ import annotations

import importlib
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGES_DIR = REPO_ROOT / "packages"

PACKAGES = ["core", "log", "api", "cli", "ui"]


@pytest.mark.parametrize("pkg", PACKAGES)
def test_package_imports_cleanly(pkg: str) -> None:
    """Each ``agent_debate_<pkg>`` package imports without error."""
    module = importlib.import_module(f"agent_debate_{pkg}")
    assert module.__name__ == f"agent_debate_{pkg}"


@pytest.mark.parametrize("pkg", PACKAGES)
def test_package_pyproject_name(pkg: str) -> None:
    """Each package declares ``name = agent_debate_<pkg>`` and src layout."""
    pyproject = PACKAGES_DIR / pkg / "pyproject.toml"
    with pyproject.open("rb") as handle:
        data = tomllib.load(handle)
    assert data["project"]["name"] == f"agent_debate_{pkg}"
    src_init = PACKAGES_DIR / pkg / "src" / f"agent_debate_{pkg}" / "__init__.py"
    assert src_init.is_file()
