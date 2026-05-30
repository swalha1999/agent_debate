"""Skeleton tests for the five workspace packages (TASKS.md 0.2 / 0.3).

The repo ships five surfaces (PRD §5.1): ``core`` (SDK), ``log`` (logging),
and the ``api`` / ``cli`` / ``ui`` surfaces. They share one PEP 420
``agent_debate`` namespace package (TASKS.md 0.3), so each surface is imported
as ``agent_debate.<pkg>``. These tests lock two contracts:

1. Each ``agent_debate.<pkg>`` package imports cleanly.
2. Each package declares the right distribution name and namespace src layout
   (no ``__init__.py`` at the ``agent_debate`` namespace level).
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
    """Each ``agent_debate.<pkg>`` package imports without error."""
    module = importlib.import_module(f"agent_debate.{pkg}")
    assert module.__name__ == f"agent_debate.{pkg}"


@pytest.mark.parametrize("pkg", PACKAGES)
def test_package_pyproject_name(pkg: str) -> None:
    """Each package declares ``name`` and the namespace src layout."""
    pyproject = PACKAGES_DIR / pkg / "pyproject.toml"
    with pyproject.open("rb") as handle:
        data = tomllib.load(handle)
    assert data["project"]["name"] == f"agent_debate_{pkg}"
    namespace_dir = PACKAGES_DIR / pkg / "src" / "agent_debate"
    # Leaf package exists, but the namespace dir itself must NOT have an
    # ``__init__.py`` (PEP 420) so the namespace can merge across packages.
    assert (namespace_dir / pkg / "__init__.py").is_file()
    assert not (namespace_dir / "__init__.py").exists()
