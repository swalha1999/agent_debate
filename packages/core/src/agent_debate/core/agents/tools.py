"""Register the debate skills as Pydantic AI tools, grouped per agent (TASKS.md 4.5).

PRD §5.2/§5.3: each agent's system prompt **names** its skills, and "Skills are real
registered tools". This module closes that loop — it wraps every skill function as a
real :class:`~pydantic_ai.Tool` whose single argument is a **Pydantic input model**, so
pydantic-ai validates the payload at the tool boundary and a malformed call raises a
``ValidationError`` before the skill runs.

Two grouping factories return the two disjoint tool sets, so the debater agents and the
controller agent each carry only their own skills (no cross-wiring):

* :func:`debater_tools` → ``web_search`` (routed through the API gatekeeper, Epic 13),
  ``build_argument``, ``analyze_opponent_argument`` — the :data:`DEBATER_SKILLS`.
* :func:`controller_tools` → ``assess_drift``, ``nudge``, ``render_verdict`` — the
  :data:`CONTROLLER_SKILLS`.

Tool **names** come from those skill-list constants and :data:`WEB_SEARCH_TOOL` (no
literal inlined), so the registered tools can never drift from the names the prompt
advertises. ``web_search`` captures ``settings``/``gatekeeper`` (built from config by the
caller) in its closure so the no-bypass property (every external call goes through the
gatekeeper) is preserved.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_debate.core.agents.controller_prompts import CONTROLLER_SKILLS
from agent_debate.core.agents.prompts import DEBATER_SKILLS
from agent_debate.core.constants import WEB_SEARCH_TOOL
from agent_debate.core.search.base import SearchResult
from agent_debate.core.skills import (
    Argument,
    ArgumentRequest,
    DriftAssessment,
    DriftRequest,
    NudgeMessage,
    NudgeRequest,
    OpponentAnalysis,
    OpponentAnalysisRequest,
    Verdict,
    VerdictRequest,
    WebSearchInput,
    analyze_opponent_argument,
    assess_drift,
    build_argument,
    nudge,
    render_verdict,
    web_search,
)
from pydantic_ai import Tool

if TYPE_CHECKING:
    from agent_debate.core.engine.gatekeeper_proto import Gatekeeper
    from agent_debate.core.settings import Settings


def _make_web_search(settings: Settings | None, gatekeeper: Gatekeeper | None) -> Tool[None]:
    """Build the ``web_search`` tool, capturing ``settings``/``gatekeeper`` in its closure.

    The captured gatekeeper is threaded into every call so the external search routes
    through the API gatekeeper (Epic 13); the no-bypass property is preserved.
    """

    def web_search_tool(request: WebSearchInput) -> list[SearchResult]:
        """Search the web for ``request.query`` (validated) via the configured provider."""
        return web_search(request.query, settings=settings, gatekeeper=gatekeeper)

    return Tool(web_search_tool, name=WEB_SEARCH_TOOL)


def _build_argument_tool(request: ArgumentRequest) -> Argument:
    """Structure ``request`` into a persuasive :class:`Argument` for the debater's side."""
    return build_argument(request)


def _analyze_opponent_tool(request: OpponentAnalysisRequest) -> OpponentAnalysis:
    """Dissect ``request`` (the opponent's last message) into an :class:`OpponentAnalysis`."""
    return analyze_opponent_argument(request)


def _assess_drift_tool(request: DriftRequest) -> DriftAssessment:
    """Classify whether the ``request`` message shows the side's agent being captured."""
    return assess_drift(request.message, request.side, request.signals)


def _nudge_tool(request: NudgeRequest) -> NudgeMessage:
    """Build a private correction for the captured ``request.agent`` (not a debate turn)."""
    return nudge(request.agent, request.reason)


def _render_verdict_tool(request: VerdictRequest) -> Verdict:
    """Structure the ``request`` transcript into a debate-derived :class:`Verdict`."""
    return render_verdict(request)


def debater_tools(
    settings: Settings | None = None,
    gatekeeper: Gatekeeper | None = None,
) -> list[Tool[None]]:
    """Return the debater tool set (PRD §5.2) — the :data:`DEBATER_SKILLS`, in order.

    ``web_search`` captures ``settings``/``gatekeeper`` so its external call routes through
    the API gatekeeper (Epic 13). Each tool's single argument is a Pydantic input model, so
    a malformed payload is rejected with a ``ValidationError`` at the tool boundary.

    Args:
        settings: Configuration the ``web_search`` provider reads; ``None`` defers to a
            fresh :class:`Settings` at call time.
        gatekeeper: The API gatekeeper every external search routes through.

    Returns:
        The three debater tools, named per :data:`DEBATER_SKILLS`.
    """
    by_name: dict[str, Tool[None]] = {
        WEB_SEARCH_TOOL: _make_web_search(settings, gatekeeper),
        "build_argument": Tool(_build_argument_tool, name="build_argument"),
        "analyze_opponent_argument": Tool(_analyze_opponent_tool, name="analyze_opponent_argument"),
    }
    return [by_name[name] for name in DEBATER_SKILLS]


def controller_tools() -> list[Tool[None]]:
    """Return the controller tool set (PRD §5.3) — the :data:`CONTROLLER_SKILLS`, in order.

    The controller skills are pure/deterministic (no external call), so they need no
    gatekeeper. Each tool's single argument is a Pydantic input model, so a malformed
    payload is rejected with a ``ValidationError`` at the tool boundary.

    Returns:
        The three controller tools, named per :data:`CONTROLLER_SKILLS`.
    """
    by_name: dict[str, Tool[None]] = {
        "assess_drift": Tool(_assess_drift_tool, name="assess_drift"),
        "nudge": Tool(_nudge_tool, name="nudge"),
        "render_verdict": Tool(_render_verdict_tool, name="render_verdict"),
    }
    return [by_name[name] for name in CONTROLLER_SKILLS]


__all__ = ["controller_tools", "debater_tools"]
