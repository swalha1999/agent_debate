"""Pin Python and lock-file contract tests (TASKS.md 0.4, issue #4).

These assertions lock in the reproducibility contract for the workspace:

* every ``pyproject.toml`` (root + each ``packages/*`` member) declares
  ``requires-python = ">=3.12"`` so the whole workspace resolves against a
  single, consistent floor;
* a top-level ``.python-version`` pins the interpreter to ``3.12`` so a fresh
  ``uv sync`` selects the same Python everywhere;
* ``uv.lock`` exists, is non-empty, and itself declares ``requires-python >=
  3.12`` — i.e. the committed lock matches the package metadata.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ROOT_PYPROJECT = REPO_ROOT / "pyproject.toml"
PACKAGE_PYPROJECTS = sorted((REPO_ROOT / "packages").glob("*/pyproject.toml"))
ALL_PYPROJECTS = [ROOT_PYPROJECT, *PACKAGE_PYPROJECTS]

REQUIRED_PYTHON = ">=3.12"
PINNED_VERSION = "3.12"


def _requires_python(pyproject: Path) -> str:
    with pyproject.open("rb") as handle:
        data = tomllib.load(handle)
    return str(data["project"]["requires-python"])


def test_packages_discovered() -> None:
    """We must actually be checking the five workspace members, not zero."""
    assert len(PACKAGE_PYPROJECTS) == 5


@pytest.mark.parametrize(
    "pyproject", ALL_PYPROJECTS, ids=lambda p: p.relative_to(REPO_ROOT).as_posix()
)
def test_requires_python_is_pinned(pyproject: Path) -> None:
    """Root and every package declare ``requires-python = ">=3.12"``."""
    assert _requires_python(pyproject) == REQUIRED_PYTHON


def test_python_version_file_pins_312() -> None:
    """A top-level ``.python-version`` pins the interpreter to 3.12."""
    version_file = REPO_ROOT / ".python-version"
    assert version_file.is_file()
    assert version_file.read_text(encoding="utf-8").strip() == PINNED_VERSION


def test_uv_lock_exists_and_non_empty() -> None:
    """The committed ``uv.lock`` exists and has content."""
    lock = REPO_ROOT / "uv.lock"
    assert lock.is_file()
    assert lock.stat().st_size > 0


def test_uv_lock_declares_requires_python() -> None:
    """``uv.lock`` itself pins ``requires-python >= 3.12``."""
    lock = REPO_ROOT / "uv.lock"
    contents = lock.read_text(encoding="utf-8")
    assert 'requires-python = ">=3.12"' in contents
