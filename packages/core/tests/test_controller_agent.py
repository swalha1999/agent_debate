"""Unit tests for the Controller agent + its system-prompt builder (TASKS.md 5.3, issue #40).

TDD red-first contract for the **third agent** (Epic 5, PRD §5.3). The deliverable is a
Pydantic AI ``Agent`` for the moderator/judge whose **system prompt**:

* states it **moderates and judges** the debate and **knows both assigned sides**
  (Pro = FOR, Con = AGAINST), spelled explicitly;
* contains an explicit **"never reveal your own stance/opinion"** instruction and does
  **not** leak a pre-held stance (anti-sycophancy ``docs/prds/anti-sycophancy.md`` §4:
  "Controller never reveals its own stance");
* is instructed to **detect drift** and **nudge privately** (a correction that does
  **not** count as a debate turn) and at the end to render a structured **verdict**;
* lists the named **controller skills** (``assess_drift``, ``nudge``, ``render_verdict``)
  with a one-line "when to use" each.

The agent is constructed with an injected pydantic-ai ``TestModel`` so the tests make
**no network call and need no API key**.
"""

from __future__ import annotations

import pydantic_ai
import pytest
from agent_debate.core import (
    CONTROLLER_SKILLS,
    build_controller_system_prompt,
    create_controller,
)
from agent_debate.core.agents import (
    CONTROLLER_SKILLS as AGENTS_CONTROLLER_SKILLS,
)
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.test import TestModel


def test_controller_skill_constant_lists_the_three_named_skills() -> None:
    assert CONTROLLER_SKILLS == ("assess_drift", "nudge", "render_verdict")
    assert AGENTS_CONTROLLER_SKILLS == CONTROLLER_SKILLS


def test_prompt_states_it_moderates_and_judges() -> None:
    lowered = build_controller_system_prompt().lower()
    assert "moderat" in lowered
    assert "judg" in lowered


def test_prompt_knows_both_sides() -> None:
    prompt = build_controller_system_prompt()
    assert "FOR" in prompt
    assert "AGAINST" in prompt


def test_prompt_has_never_reveal_stance_instruction() -> None:
    lowered = build_controller_system_prompt().lower()
    assert "never reveal" in lowered
    assert "stance" in lowered or "opinion" in lowered


def test_prompt_does_not_leak_a_pre_held_stance() -> None:
    lowered = build_controller_system_prompt().lower()
    for leak in (
        "i think pro",
        "i think con",
        "i believe the for",
        "i believe the against",
        "the for side is right",
        "the against side is right",
        "i lean",
        "in my opinion the",
    ):
        assert leak not in lowered


def test_prompt_mentions_drift_detection() -> None:
    assert "drift" in build_controller_system_prompt().lower()


def test_prompt_mentions_private_nudge_not_a_debate_turn() -> None:
    lowered = build_controller_system_prompt().lower()
    assert "nudge" in lowered
    assert "private" in lowered
    assert "does not count" in lowered or "not a debate turn" in lowered


def test_prompt_mentions_rendering_a_verdict() -> None:
    assert "verdict" in build_controller_system_prompt().lower()


def test_prompt_forbids_declaring_a_tie() -> None:
    """HW2 §8.3.6/§8.4/§9: the judge must decide — a tie is explicitly forbidden."""
    lowered = build_controller_system_prompt().lower()
    assert "tie is forbidden" in lowered or "never declare a tie" in lowered
    assert "decisive winner" in lowered or "must declare" in lowered


def test_prompt_lists_all_three_controller_skill_names() -> None:
    prompt = build_controller_system_prompt()
    for skill in ("assess_drift", "nudge", "render_verdict"):
        assert skill in prompt


def test_create_controller_returns_an_agent_without_network() -> None:
    agent = create_controller(model=TestModel())
    assert isinstance(agent, pydantic_ai.Agent)


def test_controller_agent_system_prompt_has_sides_rules_and_skills() -> None:
    agent = create_controller(model=TestModel())
    prompt = "\n".join(agent._system_prompts)  # noqa: SLF001 - inspect static prompt
    assert "FOR" in prompt
    assert "AGAINST" in prompt
    assert "never reveal" in prompt.lower()
    assert "drift" in prompt.lower()
    assert "nudge" in prompt.lower()
    assert "verdict" in prompt.lower()
    for skill in ("assess_drift", "nudge", "render_verdict"):
        assert skill in prompt


def test_controller_agent_resolves_model_from_settings_when_not_injected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # No model injected: the factory resolves the CONTROLLER model string offline.
    # A dummy key lets the eager Anthropic client construct without a network call.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key-for-offline-construction")
    monkeypatch.setenv("CONTROLLER_MODEL", "anthropic:claude-opus-4-8")
    agent = create_controller()
    assert isinstance(agent.model, AnthropicModel)
