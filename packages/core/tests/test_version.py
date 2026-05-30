"""Version-surface test for ``agent_debate.core`` (TASKS.md 0.13, issue #13).

Guideline §8.1 requires explicit version tracking starting at ``1.00``. The
canonical SDK version lives in ``agent_debate.core._version`` and is re-exported
as ``__version__`` from the package root. This test locks that contract and
asserts the legacy ``LIBRARY_VERSION`` alias stays a single source of truth.
"""

from __future__ import annotations

import re

#: The mandated initial version (guideline §8.1).
INITIAL_VERSION = "1.00"


def test_dunder_version_importable_and_value() -> None:
    """``__version__`` is importable from the core SDK and equals ``1.00``."""
    from agent_debate.core import __version__

    assert __version__ == INITIAL_VERSION


def test_dunder_version_is_well_shaped_string() -> None:
    """``__version__`` is a ``MAJOR.MINOR`` numeric string (guideline §8.1)."""
    from agent_debate.core import __version__

    assert isinstance(__version__, str)
    assert re.fullmatch(r"\d+\.\d{2}", __version__)


def test_version_module_exposes_canonical_constant() -> None:
    """The dedicated ``_version`` module is the single source of truth."""
    from agent_debate.core import _version

    assert _version.__version__ == INITIAL_VERSION


def test_library_version_aliases_dunder_version() -> None:
    """``LIBRARY_VERSION`` references ``__version__`` — no duplicate literal."""
    import agent_debate.core as core

    assert core.__version__ == core.LIBRARY_VERSION
    assert core.__version__ == core.core_version
