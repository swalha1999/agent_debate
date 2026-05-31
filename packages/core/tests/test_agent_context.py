"""Unit tests for per-agent conversation contexts (TASKS.md 5.4, issue #41).

TDD red-first contract for **independent agent contexts** (Epic 5, PRD §5.4,
anti-sycophancy ``docs/prds/anti-sycophancy.md`` §2: "Debaters never share a
chat thread"). The deliverable is plumbing — each agent keeps its OWN ordered
message history, and the two debaters' histories are ISOLATED objects so that
mutating one never touches the other (the core anti-sycophancy property).

The run loop (Epic 6) and tasks 5.5 (side anchoring re-injection) / 5.6
(adversarial relay framing) will USE these contexts; this task only builds the
isolated containers, so there is no LLM/network call here.
"""

from __future__ import annotations

from agent_debate.core import (
    AgentContext,
    DebateContexts,
    DebateSide,
    Turn,
    create_debate_contexts,
)
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart


def test_new_context_history_starts_empty() -> None:
    ctx = AgentContext(identity="pro")
    assert ctx.history() == ()


def test_append_records_an_ordered_turn() -> None:
    ctx = AgentContext(identity="pro")
    ctx.append_user("first")
    ctx.append_assistant("second")
    assert ctx.history() == (
        Turn(role="user", content="first"),
        Turn(role="assistant", content="second"),
    )


def test_history_preserves_insertion_order() -> None:
    ctx = AgentContext(identity="con")
    for i in range(5):
        ctx.append_user(str(i))
    assert [turn.content for turn in ctx.history()] == ["0", "1", "2", "3", "4"]


def test_history_is_an_immutable_snapshot() -> None:
    ctx = AgentContext(identity="pro")
    ctx.append_user("one")
    snapshot = ctx.history()
    ctx.append_user("two")
    # The earlier snapshot must not retroactively grow (it is a copy).
    assert len(snapshot) == 1


def test_two_contexts_are_distinct_objects() -> None:
    pro = AgentContext(identity="pro")
    con = AgentContext(identity="con")
    assert pro is not con


def test_appending_to_one_context_does_not_leak_into_the_other() -> None:
    # The core anti-sycophancy property: no shared chat thread.
    pro = AgentContext(identity="pro")
    con = AgentContext(identity="con")
    pro.append_user("pro-only message")
    assert con.history() == ()
    assert pro.history() == (Turn(role="user", content="pro-only message"),)


def test_holder_exposes_three_distinct_contexts() -> None:
    contexts = create_debate_contexts()
    assert isinstance(contexts, DebateContexts)
    assert contexts.pro is not contexts.con
    assert contexts.pro is not contexts.controller
    assert contexts.con is not contexts.controller


def test_holder_contexts_start_empty() -> None:
    contexts = create_debate_contexts()
    assert contexts.pro.history() == ()
    assert contexts.con.history() == ()
    assert contexts.controller.history() == ()


def test_holder_isolation_no_shared_thread() -> None:
    contexts = create_debate_contexts()
    contexts.pro.append_assistant("pro turn")
    contexts.con.append_assistant("con turn")
    assert contexts.pro.history() == (Turn(role="assistant", content="pro turn"),)
    assert contexts.con.history() == (Turn(role="assistant", content="con turn"),)
    assert contexts.controller.history() == ()


def test_holder_by_side_returns_the_matching_debater_context() -> None:
    contexts = create_debate_contexts()
    assert contexts.for_side(DebateSide.PRO) is contexts.pro
    assert contexts.for_side(DebateSide.CON) is contexts.con


def test_debater_contexts_carry_their_side_identity() -> None:
    contexts = create_debate_contexts()
    assert contexts.pro.identity == DebateSide.PRO.value
    assert contexts.con.identity == DebateSide.CON.value


def test_user_turn_maps_to_a_model_request_for_run_history() -> None:
    # Maps onto pydantic-ai message_history the engine (Epic 6) feeds to agent.run.
    message = Turn(role="user", content="hello").to_model_message()
    assert isinstance(message, ModelRequest)
    (part,) = message.parts
    assert isinstance(part, UserPromptPart)
    assert part.content == "hello"


def test_assistant_turn_maps_to_a_model_response_for_run_history() -> None:
    message = Turn(role="assistant", content="reply").to_model_message()
    assert isinstance(message, ModelResponse)
    assert message.parts == [TextPart(content="reply")]


def test_message_history_renders_own_turns_in_order() -> None:
    ctx = AgentContext(identity="pro")
    ctx.append_user("q")
    ctx.append_assistant("a")
    history = ctx.message_history()
    assert [type(m) for m in history] == [ModelRequest, ModelResponse]


def test_append_opponent_message_lands_in_own_thread_as_user_turn() -> None:
    # 5.6 will frame the opponent's message before handing it here; the context
    # must accept an already-framed opponent message as a USER turn in the
    # agent's OWN thread — never by sharing the opponent's raw history.
    pro = AgentContext(identity="pro")
    pro.append_user("Your opponent argued: «X». Rebut it.")
    assert pro.history()[-1].role == "user"
