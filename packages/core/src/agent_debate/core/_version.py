"""Canonical version surface for the agent_debate SDK (issue #13).

Guideline §8.1 ("Global Version Tracking") mandates explicit version tracking
that starts at ``1.00`` and increments on meaningful changes. This module is the
single source of truth for that literal: the package root re-exports it as
``__version__`` and the legacy ``LIBRARY_VERSION`` alias references it, so the
version string is defined in exactly one place across the workspace.
"""

from __future__ import annotations

#: SDK version (guideline §8.1). Bump on meaningful, user-visible changes.
__version__ = "1.00"

__all__ = ["__version__"]
