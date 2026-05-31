"""Unit tests for the Con debater agent (TASKS.md 5.2, issue #39).

TDD red-first contract for the **second agent** (Epic 5, PRD §5.2). The Con debater
**mirrors** the Pro debater (task 5.1): same rules and same explicit named-skill list,
only the assigned **side** flips to AGAINST. The deliverable is a Pydantic AI ``Agent``
for the CON side whose **system prompt** states:

* the assigned **side** — AGAINST (the topic), spelled explicitly;
* the **rules** — answer within ``MAX_WORDS`` words (read from config, never hard-coded);
  you MUST rebut the opponent's argument; and a do-not-concede instruction
  (anti-sycophancy ``docs/prds/anti-sycophancy.md`` §2);
* an **explicit list of the named skills** (``web_search``, ``build_argument``,
  ``analyze_opponent_argument``) with a one-line "when to use" each.

The agent is constructed with an injected pydantic-ai ``TestModel`` so the tests make
**no network call and need no API key**. The CON side resolves ``CON_MODEL`` (which falls
back to ``DEBATER_MODEL``). DRY: ``create_con_debater`` is a thin wrapper over the same
``create_debater`` seam as Pro, so the Con prompt mirrors Pro except for the side.
"""

from __future__ import annotations

import pydantic_ai
import pytest
from agent_debate.core import (
    DebateSide,
    build_debater_system_prompt,
    create_con_debater,
    create_pro_debater,
)
from agent_debate.core.agents import DEBATER_SKILLS
from agent_debate.core.settings import Settings
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.test import TestModel

_TOPIC = "Should cities ban private cars from downtown cores?"


def _prompt(**overrides: object) -> str:
    """Build a CON system prompt with a default word limit + topic, overriding kwargs."""
    fields: dict[str, object] = {"max_words": 150, "topic": _TOPIC}
    fields.update(overrides)
    return build_debater_system_prompt(DebateSide.CON, **fields)  # type: ignore[arg-type]


def test_con_prompt_states_the_against_side() -> None:
    assert "AGAINST" in _prompt()


def test_con_prompt_states_the_actual_topic_text() -> None:
    assert _TOPIC in _prompt()


def test_con_prompt_requires_rebutting_the_opponent() -> None:
    assert "rebut" in _prompt().lower()


def test_con_prompt_has_do_not_concede_instruction() -> None:
    lowered = _prompt().lower()
    assert "concede" in lowered
    assert "convincing" in lowered


def test_con_prompt_states_the_word_limit_number() -> None:
    assert "150" in _prompt(max_words=150)
    assert "99" in _prompt(max_words=99)


def test_con_prompt_lists_all_three_skill_names() -> None:
    prompt = _prompt()
    for skill in DEBATER_SKILLS:
        assert skill in prompt


def test_con_prompt_word_limit_is_config_driven() -> None:
    assert _prompt(max_words=42) != _prompt(max_words=150)
    assert "42" in _prompt(max_words=42)


def test_create_con_debater_returns_an_agent_without_network() -> None:
    agent = create_con_debater(model=TestModel(), topic=_TOPIC)
    assert isinstance(agent, pydantic_ai.Agent)


def test_con_agent_system_prompt_has_side_rules_and_skills() -> None:
    agent = create_con_debater(model=TestModel(), topic=_TOPIC)
    prompt = "\n".join(agent._system_prompts)  # noqa: SLF001 - inspect static prompt
    assert "AGAINST" in prompt
    assert "rebut" in prompt.lower()
    assert "concede" in prompt.lower()
    for skill in DEBATER_SKILLS:
        assert skill in prompt


def test_con_agent_system_prompt_states_the_topic() -> None:
    agent = create_con_debater(model=TestModel(), topic=_TOPIC)
    prompt = "\n".join(agent._system_prompts)  # noqa: SLF001 - inspect static prompt
    assert _TOPIC in prompt


def test_con_prompt_mirrors_pro_except_the_side() -> None:
    # DRY mirror: the only difference between the two debaters' prompts is the side
    # label (FOR ↔ AGAINST). Rules and skill list must be identical text otherwise.
    con = build_debater_system_prompt(DebateSide.CON, max_words=150, topic=_TOPIC)
    pro = build_debater_system_prompt(DebateSide.PRO, max_words=150, topic=_TOPIC)
    assert con != pro
    assert con.replace("AGAINST", "FOR") == pro


def test_con_agent_mirrors_pro_agent_prompt_except_side() -> None:
    con_agent = create_con_debater(model=TestModel(), topic=_TOPIC)
    pro_agent = create_pro_debater(model=TestModel(), topic=_TOPIC)
    con = "\n".join(con_agent._system_prompts)  # noqa: SLF001 - inspect static prompt
    pro = "\n".join(pro_agent._system_prompts)  # noqa: SLF001 - inspect static prompt
    assert con.replace("AGAINST", "FOR") == pro


def test_con_agent_word_limit_comes_from_settings() -> None:
    settings = Settings(max_words=77)
    agent = create_con_debater(settings, model=TestModel(), topic=_TOPIC)
    prompt = "\n".join(agent._system_prompts)  # noqa: SLF001 - inspect static prompt
    assert "77" in prompt


def test_con_agent_defaults_to_process_settings_word_limit() -> None:
    agent = create_con_debater(model=TestModel(), topic=_TOPIC)
    prompt = "\n".join(agent._system_prompts)  # noqa: SLF001 - inspect static prompt
    assert str(Settings().max_words) in prompt


def test_con_agent_resolves_con_model_from_settings_when_not_injected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # No model injected: the factory resolves the CON side's model string offline.
    # A dummy key lets the eager Anthropic client construct without a network call.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key-for-offline-construction")
    monkeypatch.setenv("CON_MODEL", "anthropic:claude-sonnet-4-6")
    settings = Settings()
    assert settings.con_model == "anthropic:claude-sonnet-4-6"
    agent = create_con_debater(settings, topic=_TOPIC)
    assert isinstance(agent.model, AnthropicModel)


def test_con_agent_con_model_falls_back_to_debater_model() -> None:
    # CON_MODEL unset: con_model falls back to debater_model (Settings default).
    settings = Settings()
    assert settings.con_model == settings.debater_model
