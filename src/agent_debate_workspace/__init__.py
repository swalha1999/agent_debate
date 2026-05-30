"""Minimal root package for the ``agent_debate`` uv workspace.

The real surfaces live under ``packages/*`` (added by tasks 0.2+). This module
exists only so the workspace root is a valid, buildable package and ``uv sync``
resolves cleanly while ``packages/*`` is still empty.
"""

__all__: list[str] = []
