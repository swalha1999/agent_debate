"""Offline helpers for the Epic-4 skills acceptance pass (issue #37).

Shared by ``test_skills_acceptance.py`` so that module stays under the 150-line
limit. Everything here is offline: a **spy gatekeeper** that records each
``execute`` call and runs it inline (proving every external call routes through
the API gatekeeper, Epic 13, with no network), and a DuckDuckGo monkeypatch that
returns canned hits (the mock provider).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from agent_debate.core.search import duckduckgo as ddg_mod

if TYPE_CHECKING:
    from pydantic_ai import Tool


class SpyGatekeeper:
    """A spy gatekeeper recording each ``execute`` call and running it inline."""

    def __init__(self) -> None:
        self.services: list[str] = []

    def execute(self, api_call: Any, *args: Any, service: str = "default", **kwargs: Any) -> Any:
        self.services += [service]
        return api_call(*args, **kwargs)


def stub_ddg(monkeypatch: Any, hits: list[dict[str, str]]) -> None:
    """Monkeypatch DuckDuckGo's single external hop to return canned ``hits``."""
    monkeypatch.setattr(
        ddg_mod.DuckDuckGoSearchProvider,
        "_fetch",
        staticmethod(lambda query, *, max_results: hits[:max_results]),
    )


def by_name(tools: list[Tool[None]], name: str) -> Tool[None]:
    """Return the registered tool named ``name`` from ``tools``."""
    return next(tool for tool in tools if tool.name == name)


def invoke(tool: Tool[None], payload: dict[str, Any]) -> Any:
    """Validate ``payload`` against ``tool``'s input model, then run its function.

    This exercises the *registered tool* end-to-end (validation + the wrapper
    body that calls the underlying skill), the seam the per-task suites only
    validate but never invoke.
    """
    validated: dict[str, Any] = tool.function_schema.validator.validate_python(payload)
    run = cast(Callable[..., Any], tool.function)  # the registered wrapper body
    return run(**validated)
