"""Per-package smoke test for ``agent_debate.log`` (TASKS.md 0.6, issue #6).

Every package owns its own ``tests/`` dir with at least one trivial passing
test (issue #6). This locks the minimal contract: the package imports cleanly
and exposes its version constant. A dedicated ``__version__`` starting at 1.00
is task 0.13; until then we assert against the ``LIBRARY_VERSION`` the package
already exposes.
"""

from __future__ import annotations


def test_log_imports_and_exposes_version() -> None:
    """``agent_debate.log`` imports and exposes its version constant."""
    import agent_debate.log as log

    assert log.__name__ == "agent_debate.log"
    assert isinstance(log.LIBRARY_VERSION, str)
    assert log.LIBRARY_VERSION
