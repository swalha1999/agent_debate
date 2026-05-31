"""Unit tests for the Pro debater agent + system-prompt builder (TASKS.md 5.1, issue #38).

TDD red-first contract for the **first agent** (Epic 5, PRD §5.2). The deliverable is a
Pydantic AI ``Agent`` for the PRO side whose **system prompt** states:

* the assigned **side** (FOR / the topic), spelled explicitly;
* the **rules** — answer within ``MAX_WORDS`` words (read from config, never hard-coded);
  you MUST rebut the opponent's argument; and a do-not-concede instruction
  (anti-sycophancy ``docs/prds/anti-sycophancy.md`` §2);
* an **explicit list of the named skills** (``web_search``, ``build_argument``,
  ``analyze_opponent_argument``) with a one-line "when to use" each.

``web_search`` is referenced **by name only** (the skill is task 4.1, not built yet); the
agent is constructed with an injected pydantic-ai ``TestModel`` so the tests make **no
network call and need no API key**.
"""

from __future__ import annotations

import pydantic_ai
import pytest
from agent_debate.core import DebateSide, build_debater_system_prompt, create_pro_debater
from agent_debate.core.agents import DEBATER_SKILLS
from agent_debate.core.settings import Settings
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.test import TestModel

_TOPIC = "Should cities ban private cars from downtown cores?"


def _prompt(**overrides: object) -> str:
    """Build a PRO system prompt with a default word limit + topic, overriding kwargs."""
    fields: dict[str, object] = {"max_words": 150, "topic": _TOPIC}
    fields.update(overrides)
    return build_debater_system_prompt(DebateSide.PRO, **fields)  # type: ignore[arg-type]


def test_prompt_states_the_actual_topic_text() -> None:
    assert _TOPIC in _prompt()


def test_skill_constant_lists_all_three_named_skills() -> None:
    assert DEBATER_SKILLS == ("web_search", "build_argument", "analyze_opponent_argument")


def test_prompt_states_the_for_side() -> None:
    prompt = _prompt()
    assert "FOR" in prompt


def test_prompt_states_the_word_limit_number() -> None:
    assert "150" in _prompt(max_words=150)
    assert "99" in _prompt(max_words=99)


def test_prompt_requires_rebutting_the_opponent() -> None:
    assert "rebut" in _prompt().lower()


def test_prompt_has_do_not_concede_instruction() -> None:
    lowered = _prompt().lower()
    assert "concede" in lowered
    assert "convincing" in lowered


def test_prompt_lists_all_three_skill_names() -> None:
    prompt = _prompt()
    for skill in ("web_search", "build_argument", "analyze_opponent_argument"):
        assert skill in prompt


def test_prompt_word_limit_is_config_driven() -> None:
    assert _prompt(max_words=42) != _prompt(max_words=150)
    assert "42" in _prompt(max_words=42)


def test_create_pro_debater_returns_an_agent_without_network() -> None:
    agent = create_pro_debater(model=TestModel(), topic=_TOPIC)
    assert isinstance(agent, pydantic_ai.Agent)


def test_pro_agent_system_prompt_has_side_rules_and_skills() -> None:
    agent = create_pro_debater(model=TestModel(), topic=_TOPIC)
    prompt = "\n".join(agent._system_prompts)  # noqa: SLF001 - inspect static prompt
    assert "FOR" in prompt
    assert "rebut" in prompt.lower()
    assert "concede" in prompt.lower()
    for skill in ("web_search", "build_argument", "analyze_opponent_argument"):
        assert skill in prompt


def test_pro_agent_system_prompt_states_the_topic() -> None:
    agent = create_pro_debater(model=TestModel(), topic=_TOPIC)
    prompt = "\n".join(agent._system_prompts)  # noqa: SLF001 - inspect static prompt
    assert _TOPIC in prompt


def test_pro_agent_word_limit_comes_from_settings() -> None:
    settings = Settings(max_words=77)
    agent = create_pro_debater(settings, model=TestModel(), topic=_TOPIC)
    prompt = "\n".join(agent._system_prompts)  # noqa: SLF001 - inspect static prompt
    assert "77" in prompt


def test_pro_agent_defaults_to_process_settings_word_limit() -> None:
    agent = create_pro_debater(model=TestModel(), topic=_TOPIC)
    prompt = "\n".join(agent._system_prompts)  # noqa: SLF001 - inspect static prompt
    assert str(Settings().max_words) in prompt


def test_pro_agent_resolves_side_model_from_settings_when_not_injected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # No model injected: the factory resolves the PRO side's model string offline.
    # A dummy key lets the eager Anthropic client construct without a network call.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key-for-offline-construction")
    monkeypatch.setenv("PRO_MODEL", "anthropic:claude-sonnet-4-6")
    settings = Settings()
    assert settings.pro_model == "anthropic:claude-sonnet-4-6"
    agent = create_pro_debater(settings, topic=_TOPIC)
    assert isinstance(agent.model, AnthropicModel)
