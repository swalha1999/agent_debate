"""Errors raised by the search provider registry (task 3.2).

:class:`UnknownSearchBackendError` is the actionable failure when
``SEARCH_BACKEND`` names a provider that is not registered: it carries the
requested key and the available backends so the message tells the operator
exactly what to set instead (sub-PRD §3 — selection is config-driven).
"""

from __future__ import annotations

from collections.abc import Sequence


class UnknownSearchBackendError(LookupError):
    """Raised when ``SEARCH_BACKEND`` names a provider that is not registered.

    Carries the offending ``backend`` key and the ``available`` registered names
    so callers/logs — and the operator reading the message — can see which value
    to set instead of the unknown one.
    """

    def __init__(self, backend: str, available: Sequence[str]) -> None:
        """Record the unknown ``backend`` key and the ``available`` names."""
        self.backend = backend
        self.available = list(available)
        listed = ", ".join(self.available) if self.available else "<none registered>"
        super().__init__(
            f"unknown search backend {backend!r}; set SEARCH_BACKEND to one of: {listed}"
        )


__all__ = ["UnknownSearchBackendError"]
