"""Per-package smoke test for ``agent_debate.cli`` (TASKS.md 0.6, issue #6).

Every package owns its own ``tests/`` dir with at least one trivial passing
test (issue #6). This locks the minimal contract: the package imports cleanly
and exposes its version constant. A dedicated ``__version__`` starting at 1.00
is task 0.13; until then we assert against the ``LIBRARY_VERSION`` the package
already exposes.
"""

from __future__ import annotations


def test_cli_imports_and_exposes_version() -> None:
    """``agent_debate.cli`` imports and exposes its version constant."""
    import agent_debate.cli as cli

    assert cli.__name__ == "agent_debate.cli"
    assert isinstance(cli.LIBRARY_VERSION, str)
    assert cli.LIBRARY_VERSION
