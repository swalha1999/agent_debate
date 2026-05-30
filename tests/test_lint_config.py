"""Lint/type-check config contract tests (TASKS.md 0.5, issue #5).

Task 0.5 fleshes out shared tooling in the root ``pyproject.toml``: a proper
ruff rule set and a strict-ish mypy config that the whole skeleton passes with
zero violations. These tests lock that config contract so a later edit cannot
silently weaken the gate:

* ``[tool.ruff]`` selects at least the E/F/I/UP/B rule families and declares an
  explicit ``line-length``;
* ``[tool.mypy]`` is strict-ish — ``disallow_untyped_defs``,
  ``warn_unused_ignores`` and ``no_implicit_optional`` are all on — while the
  PEP 420 namespace settings from task 0.3 stay in place.

This is the pragmatic TDD for a config-only task: a config-presence test that
fails before the config exists and passes once it does. The end-to-end proof
(``ruff check .`` / ``mypy`` clean) is enforced by CI and the build harness.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ROOT_PYPROJECT = REPO_ROOT / "pyproject.toml"

#: Rule families the lint gate must select (issue #5: "E,F,I,UP,B etc.").
REQUIRED_RUFF_FAMILIES = {"E", "F", "I", "UP", "B"}

#: Strict-ish mypy switches that must be enabled on top of ``strict``.
REQUIRED_MYPY_FLAGS = (
    "disallow_untyped_defs",
    "warn_unused_ignores",
    "no_implicit_optional",
)


def _root_config() -> dict[str, object]:
    with ROOT_PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)


def test_ruff_selects_required_rule_families() -> None:
    """``[tool.ruff.lint]`` selects at least E/F/I/UP/B."""
    tool = _root_config()["tool"]
    assert isinstance(tool, dict)
    selected = set(tool["ruff"]["lint"]["select"])
    assert selected >= REQUIRED_RUFF_FAMILIES


def test_ruff_declares_line_length() -> None:
    """``[tool.ruff]`` declares an explicit, positive ``line-length``."""
    tool = _root_config()["tool"]
    assert isinstance(tool, dict)
    line_length = tool["ruff"]["line-length"]
    assert isinstance(line_length, int)
    assert line_length > 0


def test_mypy_is_strict_ish() -> None:
    """``[tool.mypy]`` enables the strict-ish flags this repo requires."""
    tool = _root_config()["tool"]
    assert isinstance(tool, dict)
    mypy = tool["mypy"]
    for flag in REQUIRED_MYPY_FLAGS:
        assert mypy[flag] is True, f"mypy.{flag} must be True"


def test_mypy_keeps_namespace_settings() -> None:
    """The PEP 420 namespace settings from task 0.3 stay enabled."""
    tool = _root_config()["tool"]
    assert isinstance(tool, dict)
    mypy = tool["mypy"]
    assert mypy["namespace_packages"] is True
    assert mypy["explicit_package_bases"] is True
