"""Per-turn side-anchoring builder + injection helper (TASKS.md 5.5, issue #42).

Anti-sycophancy (``docs/prds/anti-sycophancy.md`` §2 mechanism 2): before EACH
debater turn the agent's assigned side (FOR/AGAINST) plus an explicit "do not
concede merely because the opponent is convincing" instruction is re-injected —
in ADDITION to the system prompt, as a per-turn reminder. These tests pin that:

* :func:`build_side_anchor` states the right side label and the anti-concession
  instruction for PRO (FOR) and CON (AGAINST);
* :func:`anchor_turn` injects the anchor as a ``user`` turn into THAT agent's OWN
  context only (reuses the 5.4 isolation) — and adds it on EVERY round.
"""

from __future__ import annotations

from agent_debate.core.agents.anchoring import (
    ANTI_CONCESSION_RULE,
    build_side_anchor,
)
from agent_debate.core.agents.context import create_debate_contexts
from agent_debate.core.agents.prompts import SIDE_LABEL
from agent_debate.core.skills import DebateSide
from agent_debate.log import get_logger


def test_anchor_pro_states_for_side() -> None:
    """The PRO anchor names the FOR side explicitly (PRD §5.2 side labels)."""
    anchor = build_side_anchor(DebateSide.PRO)
    assert SIDE_LABEL[DebateSide.PRO] in anchor
    assert "FOR" in anchor


def test_anchor_con_states_against_side() -> None:
    """The CON anchor names the AGAINST side explicitly."""
    anchor = build_side_anchor(DebateSide.CON)
    assert SIDE_LABEL[DebateSide.CON] in anchor
    assert "AGAINST" in anchor


def test_anchor_includes_anti_concession_instruction() -> None:
    """Every anchor carries the explicit do-not-concede instruction (§2.2)."""
    for side in DebateSide:
        anchor = build_side_anchor(side)
        lowered = anchor.lower()
        assert "do not concede" in lowered
        assert "convincing" in lowered


def test_anchor_shares_one_anti_concession_source() -> None:
    """The anti-concession wording is the ONE shared constant (DRY, not re-typed)."""
    assert ANTI_CONCESSION_RULE in build_side_anchor(DebateSide.PRO)
    assert ANTI_CONCESSION_RULE in build_side_anchor(DebateSide.CON)


def test_anchor_word_limit_optional() -> None:
    """When ``max_words`` is given the anchor mentions the limit; else it does not."""
    with_limit = build_side_anchor(DebateSide.PRO, max_words=42)
    assert "42" in with_limit
    assert "42" not in build_side_anchor(DebateSide.PRO)


def test_anchor_turn_injects_into_own_context_only() -> None:
    """Anchoring the Pro turn appends to Pro's history and NOT Con's (5.4 isolation)."""
    from agent_debate.core.agents.anchoring import anchor_turn

    contexts = create_debate_contexts()
    anchor_turn(contexts.for_side(DebateSide.PRO), DebateSide.PRO)

    pro_turns = contexts.pro.history()
    assert len(pro_turns) == 1
    assert pro_turns[0].role == "user"
    assert SIDE_LABEL[DebateSide.PRO] in pro_turns[0].content
    assert contexts.con.history() == ()


def test_anchor_turn_present_each_round() -> None:
    """Anchoring twice adds the reminder both rounds — present on EVERY turn."""
    from agent_debate.core.agents.anchoring import anchor_turn

    contexts = create_debate_contexts()
    ctx = contexts.for_side(DebateSide.CON)
    anchor_turn(ctx, DebateSide.CON)
    anchor_turn(ctx, DebateSide.CON)

    turns = ctx.history()
    assert len(turns) == 2
    assert all(SIDE_LABEL[DebateSide.CON] in turn.content for turn in turns)


def test_anchor_turn_can_combine_with_relayed_opponent_message() -> None:
    """The anchor composes with a (future 5.6) relayed opponent message in one turn."""
    from agent_debate.core.agents.anchoring import anchor_turn

    contexts = create_debate_contexts()
    relayed = "Your opponent argued: «X». Rebut it."
    anchor_turn(contexts.pro, DebateSide.PRO, opponent_message=relayed)

    turns = contexts.pro.history()
    assert len(turns) == 1
    assert relayed in turns[0].content
    assert SIDE_LABEL[DebateSide.PRO] in turns[0].content


def test_anchor_turn_returns_injected_text() -> None:
    """``anchor_turn`` returns the exact text it appended (so callers can log it)."""
    from agent_debate.core.agents.anchoring import anchor_turn

    contexts = create_debate_contexts()
    injected = anchor_turn(contexts.pro, DebateSide.PRO)
    assert contexts.pro.history()[0].content == injected


def test_log_module_importable() -> None:
    """The anchoring module logs via the LOG package (smoke)."""
    assert get_logger("agents") is not None
