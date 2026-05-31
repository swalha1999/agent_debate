"""Debater agent factory — builds the Pydantic AI ``Agent`` (TASKS.md 5.1, issue #38).

PRD §5.2: each debater is a Pydantic AI :class:`~pydantic_ai.Agent` configured with a
system prompt that states its side, the rules, and its explicit skill list. This module
wires that together: it resolves the side's model from :class:`~agent_debate.core.Settings`
(``PRO_MODEL`` / ``CON_MODEL`` → ``DEBATER_MODEL`` fallback, via
:func:`~agent_debate.core.resolve_model`) and sets ``system_prompt`` from
:func:`~agent_debate.core.agents.prompts.build_debater_system_prompt`.

The factory is **side-parameterizable** via :func:`create_debater`, so the Con debater
(task 5.2) reuses it; :func:`create_pro_debater` is the task-5.1 entry point. A ``model``
may be **injected** (e.g. a pydantic-ai ``TestModel``) so tests construct the agent with
no network call and no API key — and so the eager Anthropic client (which needs
``ANTHROPIC_API_KEY``) is never built in tests.

The skills are registered as real Pydantic AI tools (task 4.5) via
:func:`~agent_debate.core.agents.tools.debater_tools`, so the agent carries both the
**system prompt** (side, rules, skill list) AND those skills as validated, callable tools.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_debate.core.agents.prompts import build_debater_system_prompt
from agent_debate.core.agents.tools import debater_tools
from agent_debate.core.models import resolve_model
from agent_debate.core.settings import Settings, get_settings
from agent_debate.core.skills import DebateSide
from agent_debate.log import get_logger
from pydantic_ai import Agent
from pydantic_ai.models import Model

if TYPE_CHECKING:
    from agent_debate.core.engine.gatekeeper_proto import Gatekeeper

_LOG = get_logger("agents")

#: Maps each side to the :class:`Settings` attribute holding its resolved model
#: string (honouring the per-side → ``DEBATER_MODEL`` fallback). Kept here so the
#: side→model wiring is defined once and the Con debater (task 5.2) reuses it.
_SIDE_MODEL_ATTR: dict[DebateSide, str] = {
    DebateSide.PRO: "pro_model",
    DebateSide.CON: "con_model",
}


def create_debater(
    side: DebateSide,
    settings: Settings | None = None,
    *,
    model: Model | None = None,
    gatekeeper: Gatekeeper | None = None,
) -> Agent[None, str]:
    """Build a debater :class:`~pydantic_ai.Agent` for ``side`` (PRD §5.2).

    The agent's ``system_prompt`` is built from config: the per-message word limit
    is read from ``settings.max_words`` (never hard-coded). When ``model`` is given
    it is used as-is (tests inject a ``TestModel`` to avoid any network/key); else
    the side's configured model string is resolved offline. The three debater skills
    (:func:`~agent_debate.core.agents.tools.debater_tools`) are registered as real
    Pydantic AI tools, with ``web_search`` routed through the API gatekeeper.

    Args:
        side: The assigned stance — ``PRO`` or ``CON``.
        settings: Configuration to read; defaults to the process settings.
        model: An optional pre-built model to inject (skips string resolution).
        gatekeeper: The API gatekeeper ``web_search`` routes its external call through.

    Returns:
        The configured debater agent, with its skills registered as tools.
    """
    resolved_settings = settings or get_settings()
    agent_model: Model | str
    if model is not None:
        agent_model = model
    else:
        model_string = getattr(resolved_settings, _SIDE_MODEL_ATTR[side])
        agent_model = resolve_model(model_string)
    prompt = build_debater_system_prompt(side, max_words=resolved_settings.max_words)
    tools = debater_tools(resolved_settings, gatekeeper)
    _LOG.debug("debater_created", side=side.value, max_words=resolved_settings.max_words)
    return Agent(agent_model, system_prompt=prompt, tools=tools)


def create_pro_debater(
    settings: Settings | None = None,
    *,
    model: Model | None = None,
    gatekeeper: Gatekeeper | None = None,
) -> Agent[None, str]:
    """Build the **Pro** debater (side=FOR) — the task-5.1 entry point (issue #38).

    Thin wrapper over :func:`create_debater` with ``side=PRO``; see it for argument
    semantics. The Con debater (task 5.2) gets its own wrapper over the same seam.
    """
    return create_debater(DebateSide.PRO, settings, model=model, gatekeeper=gatekeeper)


def create_con_debater(
    settings: Settings | None = None,
    *,
    model: Model | None = None,
    gatekeeper: Gatekeeper | None = None,
) -> Agent[None, str]:
    """Build the **Con** debater (side=AGAINST) — the task-5.2 entry point (issue #39).

    Mirror of :func:`create_pro_debater`: a thin wrapper over :func:`create_debater`
    with ``side=CON`` so the Con agent reuses the exact same rules and skill list as
    Pro (DRY), only the assigned side flips. Its model resolves from ``CON_MODEL``
    (falling back to ``DEBATER_MODEL``); see :func:`create_debater` for argument
    semantics.
    """
    return create_debater(DebateSide.CON, settings, model=model, gatekeeper=gatekeeper)


__all__ = ["create_con_debater", "create_debater", "create_pro_debater"]
