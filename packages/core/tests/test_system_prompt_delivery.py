"""System-prompt delivery on the message_history path (fix/system-prompt-delivery).

Root-cause regression suite. pydantic-ai does NOT re-inject an ``Agent``'s
configured ``system_prompt`` once a run is given a ``message_history`` — and the
engine ALWAYS supplies one (each agent's isolated :class:`AgentContext`). Before
the fix the model therefore received NO ``SystemPromptPart`` at all: debaters ran
with no assigned side, no rules, no skills list and no topic.

These tests drive the REAL engine turn/closing path with a ``FunctionModel`` that
captures the full ``ModelMessage`` list and assert the model now receives the
debater's full system prompt (side label + topic + a skill name) as a leading
``SystemPromptPart`` — delivered exactly ONCE across a multi-turn run (not
duplicated per turn). All offline: no network, no key.
"""

from __future__ import annotations

from pathlib import Path

from _engine_acceptance_helpers import config, gatekeeper, message_capturing_model, models
from agent_debate.core import DebateSide, setup_debate
from agent_debate.core.engine.closing import run_closing_discussion
from agent_debate.core.engine.turn import run_debate_turn
from pydantic_ai.messages import ModelMessage, SystemPromptPart
from pydantic_ai.models.test import TestModel

_TOPIC = "Should city parks ban gas-powered leaf blowers?"
_FOR = "FOR"
_AGAINST = "AGAINST"
_A_SKILL = "web_search"


def _system_texts(messages: list[ModelMessage]) -> list[str]:
    """Collect every ``SystemPromptPart`` content across a captured message list."""
    return [
        part.content
        for message in messages
        for part in getattr(message, "parts", [])
        if isinstance(part, SystemPromptPart)
    ]


def _run_pro_turn(rounds: int, runs_dir: Path, captured: list[list[ModelMessage]]) -> None:
    """Drive ``rounds`` real Pro turns through the engine path into ``captured``."""
    cfg = config(rounds=rounds, max_words=50)
    setup = setup_debate(
        _TOPIC,
        cfg,
        models=models(pro=message_capturing_model("Pro.", captured), con=TestModel()),
    )
    keeper = gatekeeper("sp-run", runs_dir)
    opponent: str | None = None
    for round_ in range(1, rounds + 1):
        run_debate_turn(
            agent=setup.pro_agent,
            context=setup.contexts.for_side(DebateSide.PRO),
            side=DebateSide.PRO,
            round_=round_,
            config=cfg,
            gatekeeper=keeper,
            run_id="sp-run",
            runs_dir=runs_dir,
            opponent_message=opponent,
        )
        opponent = "Con says no."


def test_debater_system_prompt_reaches_the_model(tmp_path: Path) -> None:
    # RED before the fix: the captured history carried no SystemPromptPart.
    captured: list[list[ModelMessage]] = []
    _run_pro_turn(1, tmp_path, captured)
    (texts,) = [_system_texts(msgs) for msgs in captured]
    assert len(texts) == 1
    prompt = texts[0]
    assert _FOR in prompt
    assert _TOPIC in prompt
    assert _A_SKILL in prompt


def test_system_prompt_injected_exactly_once_across_turns(tmp_path: Path) -> None:
    # The prompt must lead the FIRST request only — never repeated per turn.
    captured: list[list[ModelMessage]] = []
    _run_pro_turn(3, tmp_path, captured)
    assert len(captured) == 3
    for msgs in captured:
        assert len(_system_texts(msgs)) == 1


def test_con_side_label_is_isolated_to_con(tmp_path: Path) -> None:
    # 5.4 isolation: each agent only ever sees its OWN prompt (AGAINST for Con).
    captured: list[list[ModelMessage]] = []
    cfg = config(rounds=1, max_words=50)
    setup = setup_debate(
        _TOPIC,
        cfg,
        models=models(pro=TestModel(), con=message_capturing_model("Con.", captured)),
    )
    run_debate_turn(
        agent=setup.con_agent,
        context=setup.contexts.for_side(DebateSide.CON),
        side=DebateSide.CON,
        round_=1,
        config=cfg,
        gatekeeper=gatekeeper("sp-con", tmp_path),
        run_id="sp-con",
        runs_dir=tmp_path,
        opponent_message="Pro says yes.",
    )
    (texts,) = [_system_texts(msgs) for msgs in captured]
    assert _AGAINST in texts[0]
    assert _FOR not in texts[0]


def test_closing_discussion_still_carries_the_system_prompt(tmp_path: Path) -> None:
    # The closing phase reuses the debater contexts, so its calls must still
    # deliver the system prompt (with the topic) to the model.
    captured: list[list[ModelMessage]] = []
    cfg = config(rounds=1, max_words=50)
    setup = setup_debate(
        _TOPIC,
        cfg,
        models=models(
            pro=message_capturing_model("Pro.", captured),
            con=message_capturing_model("Con.", captured),
        ),
    )
    run_closing_discussion(
        setup,
        cfg,
        gatekeeper=gatekeeper("sp-close", tmp_path),
        run_id="sp-close",
        runs_dir=tmp_path,
    )
    assert captured
    for msgs in captured:
        texts = _system_texts(msgs)
        assert len(texts) == 1
        assert _TOPIC in texts[0]
