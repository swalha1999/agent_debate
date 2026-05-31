"""Re-export shim for the Epic-5 agents surface (PRD §5.2–§5.7).

The :mod:`agent_debate.core` hub aggregates every subpackage's public names, so it
sits near the 150-code-line guideline (PRD §3.2). The agents subpackage exposes the
largest single group (debaters, controller, contexts, anchoring, relay, word limit),
so its re-export block is factored out here and pulled into ``__init__`` with a single
``from ._agents_public import *`` (split, not compress). This module re-exports the
:mod:`agent_debate.core.agents` public surface verbatim — it adds no behaviour.
"""

from __future__ import annotations

from agent_debate.core.agents import (
    ADVERSARIAL_RELAY_TEMPLATE,
    ANTI_CONCESSION_RULE,
    CONTROLLER_SKILLS,
    DEBATER_SKILLS,
    AgentContext,
    DebateContexts,
    Turn,
    WordLimitResult,
    anchor_turn,
    build_adversarial_relay,
    build_controller_system_prompt,
    build_debater_system_prompt,
    build_side_anchor,
    count_words,
    create_con_debater,
    create_controller,
    create_debate_contexts,
    create_debater,
    create_pro_debater,
    enforce_word_limit,
    relay_opponent_turn,
)

__all__ = [
    "ADVERSARIAL_RELAY_TEMPLATE",
    "ANTI_CONCESSION_RULE",
    "AgentContext",
    "CONTROLLER_SKILLS",
    "DEBATER_SKILLS",
    "DebateContexts",
    "Turn",
    "WordLimitResult",
    "anchor_turn",
    "build_adversarial_relay",
    "build_controller_system_prompt",
    "build_debater_system_prompt",
    "build_side_anchor",
    "count_words",
    "create_con_debater",
    "create_controller",
    "create_debate_contexts",
    "create_debater",
    "create_pro_debater",
    "enforce_word_limit",
    "relay_opponent_turn",
]
