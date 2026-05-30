"""Per-package smoke test for ``agent_debate.api`` (TASKS.md 0.6, issue #6).

Every package owns its own ``tests/`` dir with at least one trivial passing
test (issue #6). This locks the minimal contract: the package imports cleanly
and exposes its version constant. A dedicated ``__version__`` starting at 1.00
is task 0.13; until then we assert against the ``LIBRARY_VERSION`` the package
already exposes.
"""

from __future__ import annotations


def test_api_imports_and_exposes_version() -> None:
    """``agent_debate.api`` imports and exposes its version constant."""
    import agent_debate.api as api

    assert api.__name__ == "agent_debate.api"
    assert isinstance(api.LIBRARY_VERSION, str)
    assert api.LIBRARY_VERSION
