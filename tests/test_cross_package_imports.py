"""Cross-package import tests for the workspace deps (TASKS.md 0.3, issue #3).

The dependency graph (issue #3) is: ``core`` depends on ``log``; ``api`` /
``cli`` / ``ui`` depend on both ``core`` and ``log``. Each base package exposes
a version constant and each dependent re-exports the value it imports across the
edge, so a successful import proves the edge resolves at runtime.

These tests also lock the PEP 420 contract: the ``agent_debate`` namespace must
merge across all five distributions, so two different subpackages must be
importable together in the same interpreter.
"""

from __future__ import annotations

import importlib


def test_core_imports_log() -> None:
    """``core`` re-exports ``log``'s version (core -> log edge)."""
    import agent_debate.core as core
    import agent_debate.log as log

    assert core.log_version == log.log_version


def test_dependents_import_core_and_log() -> None:
    """api/cli/ui re-export both ``core`` and ``log`` versions (both edges)."""
    import agent_debate.core as core
    import agent_debate.log as log

    for name in ("api", "cli", "ui"):
        surface = importlib.import_module(f"agent_debate.{name}")
        assert surface.core_version == core.core_version
        assert surface.log_version == log.log_version


def test_namespace_merges() -> None:
    """The ``agent_debate`` namespace merges: two subpackages import together."""
    import agent_debate.core
    import agent_debate.log

    # Same parent namespace object, distinct leaf modules from distinct dists.
    assert agent_debate.core.__name__ == "agent_debate.core"
    assert agent_debate.log.__name__ == "agent_debate.log"
    # PEP 420 namespace: the parent has no single ``__file__`` (multiple paths).
    import agent_debate

    assert not hasattr(agent_debate, "__file__") or agent_debate.__file__ is None
    assert len(list(agent_debate.__path__)) >= 2
