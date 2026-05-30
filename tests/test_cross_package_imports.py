"""Cross-package import contract tests (TASKS.md 0.3).

Task 0.3 wires the intra-workspace dependency graph (PRD §5.1, §5.7):

* ``core`` depends on ``log``.
* ``api`` / ``cli`` / ``ui`` depend on **both** ``core`` and ``log``.

These tests lock that the dependencies are not just declared in each
``pyproject.toml`` but actually *resolve at runtime* — i.e. a surface package
can import names from the packages it depends on. To prove it, each dependent
package exposes a tiny re-export of the ``LIBRARY_VERSION`` constant from its
dependencies; importing those names exercises the real cross-package edges.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGES_DIR = REPO_ROOT / "packages"

# Dependency graph wired by this task: package -> the packages it imports from.
DEPENDENCY_GRAPH: dict[str, tuple[str, ...]] = {
    "core": ("log",),
    "api": ("core", "log"),
    "cli": ("core", "log"),
    "ui": ("core", "log"),
}


@pytest.mark.parametrize(
    ("pkg", "dependency"),
    [(pkg, dep) for pkg, deps in DEPENDENCY_GRAPH.items() for dep in deps],
)
def test_dependency_declared_in_pyproject(pkg: str, dependency: str) -> None:
    """Each package declares its intra-workspace deps under ``[project]``."""
    pyproject = PACKAGES_DIR / pkg / "pyproject.toml"
    with pyproject.open("rb") as handle:
        data = tomllib.load(handle)
    deps = data["project"]["dependencies"]
    assert f"agent_debate_{dependency}" in deps
    # And the dep is sourced from the local workspace, not PyPI.
    sources = data["tool"]["uv"]["sources"]
    assert sources[f"agent_debate_{dependency}"] == {"workspace": True}


@pytest.mark.parametrize(
    ("pkg", "dependency"),
    [(pkg, dep) for pkg, deps in DEPENDENCY_GRAPH.items() for dep in deps],
)
def test_cross_package_import_resolves(pkg: str, dependency: str) -> None:
    """A dependent package can import a name from each package it depends on.

    Each dependent re-exports ``<dep>_version`` sourced from the dependency's
    ``LIBRARY_VERSION``; equality proves the edge resolves at runtime.
    """
    import importlib

    consumer = importlib.import_module(f"agent_debate_{pkg}")
    dependency_mod = importlib.import_module(f"agent_debate_{dependency}")
    reexport = getattr(consumer, f"{dependency}_version")
    assert reexport == dependency_mod.LIBRARY_VERSION
