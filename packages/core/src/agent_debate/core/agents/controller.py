"""Controller agent factory — builds the Pydantic AI ``Agent`` (TASKS.md 5.3, issue #40).

PRD §5.3: the Controller is a Pydantic AI :class:`~pydantic_ai.Agent` configured with the
moderator/judge system prompt (it knows both sides, never reveals its own stance, detects
drift + nudges, and renders a verdict). This module wires that together: it resolves the
controller model from :class:`~agent_debate.core.Settings` (``CONTROLLER_MODEL`` via
:func:`~agent_debate.core.resolve_model`) and sets ``system_prompt`` from
:func:`~agent_debate.core.agents.controller_prompts.build_controller_system_prompt`.

A ``model`` may be **injected** (e.g. a pydantic-ai ``TestModel``) so tests construct the
agent with no network call and no API key. Registering the controller skills as real
Pydantic AI tools is a later task; here the deliverable is the agent carrying the correct
moderator/judge **system prompt** (both sides, neutrality, drift/nudge/verdict, skills).
"""

from __future__ import annotations

from agent_debate.core.agents.controller_prompts import build_controller_system_prompt
from agent_debate.core.models import resolve_model
from agent_debate.core.settings import Settings, get_settings
from agent_debate.log import get_logger
from pydantic_ai import Agent
from pydantic_ai.models import Model

_LOG = get_logger("agents")


def create_controller(
    settings: Settings | None = None,
    *,
    model: Model | None = None,
) -> Agent[None, str]:
    """Build the Controller :class:`~pydantic_ai.Agent` (PRD §5.3, anti-sycophancy §4).

    The agent's ``system_prompt`` is the moderator/judge prompt: it knows both sides
    (Pro = FOR, Con = AGAINST), must NEVER reveal its own stance, detects drift, nudges
    privately (not a debate turn), and renders a verdict. When ``model`` is given it is
    used as-is (tests inject a ``TestModel`` to avoid any network/key); otherwise the
    configured ``CONTROLLER_MODEL`` string is resolved offline.

    Args:
        settings: Configuration to read; defaults to the process settings.
        model: An optional pre-built model to inject (skips string resolution).

    Returns:
        The configured controller agent.
    """
    resolved_settings = settings or get_settings()
    agent_model: Model | str = (
        model if model is not None else resolve_model(resolved_settings.controller_model)
    )
    prompt = build_controller_system_prompt()
    _LOG.debug("controller_created", model=resolved_settings.controller_model)
    return Agent(agent_model, system_prompt=prompt)


__all__ = ["create_controller"]
