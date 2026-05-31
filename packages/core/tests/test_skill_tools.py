"""Unit tests for registering skills as Pydantic AI tools (TASKS.md 4.5, issue #36).

TDD red-first contract for **tool registration** (Epic 4, PRD §5.2/§5.3). The
deliverable is: every named skill is attached to its agent as a real Pydantic AI
:class:`~pydantic_ai.Tool` whose single argument is a **Pydantic input model**, so a
malformed payload is rejected at the tool boundary (``ValidationError``). The skills
are grouped into a **debater** tool set (``web_search``, ``build_argument``,
``analyze_opponent_argument``) and a **controller** tool set (``assess_drift``,
``nudge``, ``render_verdict``); each agent carries only its own set.

The agents are built with an injected pydantic-ai ``TestModel`` so the tests make
**no network call and need no API key** — they only *inspect* the registered tools
and exercise each tool's input validator, never run a full LLM loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from agent_debate.core.agents import (
    CONTROLLER_SKILLS,
    DEBATER_SKILLS,
    controller_tools,
    create_con_debater,
    create_controller,
    create_pro_debater,
    debater_tools,
)
from pydantic import ValidationError
from pydantic_ai.models.test import TestModel

if TYPE_CHECKING:
    from pydantic_ai import Agent, Tool


_TOPIC = "Should cities ban private cars from downtown cores?"


def _tool_names(agent: Agent[None, str]) -> set[str]:
    """Return the names of the tools registered on ``agent`` (introspection seam)."""
    return set(agent._function_toolset.tools)  # noqa: SLF001 - inspect registered tools


def _validate(tool: Tool[None], payload: dict[str, object]) -> None:
    """Run a tool's input validator over a raw ``payload`` (raises on malformed input)."""
    tool.function_schema.validator.validate_python(payload)


def _by_name(tools: list[Tool[None]], name: str) -> Tool[None]:
    return next(tool for tool in tools if tool.name == name)


def test_debater_tools_returns_the_three_debater_skills() -> None:
    names = {tool.name for tool in debater_tools()}
    assert names == set(DEBATER_SKILLS)


def test_controller_tools_returns_the_three_controller_skills() -> None:
    names = {tool.name for tool in controller_tools()}
    assert names == set(CONTROLLER_SKILLS)


def test_pro_debater_has_the_three_debater_tools_registered() -> None:
    agent = create_pro_debater(model=TestModel(), topic=_TOPIC)
    assert _tool_names(agent) == set(DEBATER_SKILLS)


def test_con_debater_has_the_three_debater_tools_registered() -> None:
    agent = create_con_debater(model=TestModel(), topic=_TOPIC)
    assert _tool_names(agent) == set(DEBATER_SKILLS)


def test_controller_has_the_three_controller_tools_registered() -> None:
    agent = create_controller(model=TestModel())
    assert _tool_names(agent) == set(CONTROLLER_SKILLS)


def test_debater_and_controller_tool_sets_are_disjoint() -> None:
    debater = _tool_names(create_pro_debater(model=TestModel(), topic=_TOPIC))
    controller = _tool_names(create_controller(model=TestModel()))
    assert debater.isdisjoint(controller)


def test_debater_has_no_controller_tools() -> None:
    agent = create_pro_debater(model=TestModel(), topic=_TOPIC)
    assert _tool_names(agent) & set(CONTROLLER_SKILLS) == set()


def test_controller_has_no_debater_tools() -> None:
    agent = create_controller(model=TestModel())
    assert _tool_names(agent) & set(DEBATER_SKILLS) == set()


def test_tool_names_match_the_prompt_advertised_skill_names() -> None:
    # The tool names must equal the names the system prompt advertises (no drift).
    assert {tool.name for tool in debater_tools()} == set(DEBATER_SKILLS)
    assert {tool.name for tool in controller_tools()} == set(CONTROLLER_SKILLS)


def test_web_search_tool_rejects_malformed_payload() -> None:
    tool = _by_name(debater_tools(), "web_search")
    with pytest.raises(ValidationError):
        _validate(tool, {"request": {"query": "   "}})


def test_build_argument_tool_rejects_malformed_payload() -> None:
    tool = _by_name(debater_tools(), "build_argument")
    with pytest.raises(ValidationError):
        _validate(tool, {"request": {"side": "pro", "claim": "", "supports": []}})


def test_analyze_opponent_tool_rejects_malformed_payload() -> None:
    tool = _by_name(debater_tools(), "analyze_opponent_argument")
    with pytest.raises(ValidationError):
        _validate(tool, {"request": {"side": "sideways", "opponent_message": "x"}})


def test_assess_drift_tool_rejects_malformed_payload() -> None:
    tool = _by_name(controller_tools(), "assess_drift")
    with pytest.raises(ValidationError):
        _validate(tool, {"request": {"message": "", "side": "pro"}})


def test_nudge_tool_rejects_malformed_payload() -> None:
    tool = _by_name(controller_tools(), "nudge")
    with pytest.raises(ValidationError):
        _validate(tool, {"request": {"agent": "pro", "reason": ""}})


def test_nudge_tool_rejects_whitespace_only_reason() -> None:
    # Passes ``min_length`` but the strip validator rejects whitespace-only reasons.
    tool = _by_name(controller_tools(), "nudge")
    with pytest.raises(ValidationError):
        _validate(tool, {"request": {"agent": "pro", "reason": "   "}})


def test_render_verdict_tool_rejects_malformed_payload() -> None:
    tool = _by_name(controller_tools(), "render_verdict")
    with pytest.raises(ValidationError):
        _validate(tool, {"request": {"turns": []}})


def test_build_argument_tool_accepts_a_valid_payload() -> None:
    tool = _by_name(debater_tools(), "build_argument")
    _validate(tool, {"request": {"side": "pro", "claim": "c", "supports": ["s"]}})
