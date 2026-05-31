"""Debate agents subpackage — the Pydantic AI ``Agent``s (Epic 5).

PRD §5.2: the system has three agents (Pro debater, Con debater, Controller), each a
Pydantic AI :class:`~pydantic_ai.Agent` with its own independent conversation context.
This subpackage holds the **debater** agents and the shared system-prompt builder.

Task 5.1 (issue #38) ships the **Pro** debater:

* :func:`~agent_debate.core.agents.prompts.build_debater_system_prompt` — the pure prompt
  builder that states the side (FOR/AGAINST), the rules (``<= max_words`` words, must
  rebut, do not concede merely because the opponent is convincing — anti-sycophancy §2)
  and the explicit named skill list (:data:`DEBATER_SKILLS`).
* :func:`~agent_debate.core.agents.debater.create_pro_debater` — the factory that builds
  the PRO agent, over a side-parameterizable :func:`create_debater` seam.

Task 5.2 (issue #39) adds :func:`~agent_debate.core.agents.debater.create_con_debater` —
the **Con** (AGAINST) debater, a thin mirror of the Pro wrapper over the same
:func:`create_debater` seam (same rules and skill list, only the side flips).

Task 5.3 (issue #40) adds the **Controller** (moderator/judge):
:func:`~agent_debate.core.agents.controller_prompts.build_controller_system_prompt` (it
knows both sides, NEVER reveals its own stance, detects drift + nudges privately, renders
a verdict, and lists :data:`CONTROLLER_SKILLS`) and the
:func:`~agent_debate.core.agents.controller.create_controller` factory over the resolved
``CONTROLLER_MODEL``.

Task 5.4 (issue #41) adds **independent agent contexts**
(:mod:`~agent_debate.core.agents.context`): :class:`AgentContext` (one agent's OWN
ordered history), :class:`Turn` (typed ``role``/``content`` record mapping to
pydantic-ai ``message_history``), the :class:`DebateContexts` holder and
:func:`create_debate_contexts` — three ISOLATED contexts so the two debaters never
share a chat thread (anti-sycophancy §2).

Task 5.6 (issue #43) adds the **adversarial relay**
(:mod:`~agent_debate.core.agents.relay`): :func:`build_adversarial_relay` frames
the opponent's (sanitised) last message as *"Your opponent argued: «…». Rebut
it."* and :func:`relay_opponent_turn` injects it — together with the side anchor
— as a ``user`` turn into the agent's OWN context (anti-sycophancy §2 mechanism 1).

Task 5.7 (issue #44) adds **post-generation word-limit enforcement**
(:mod:`~agent_debate.core.agents.word_limit`): :func:`count_words` (the
whitespace-split counting rule) and :func:`enforce_word_limit`, which the engine
(Epic 6) calls after each turn — if the message exceeds ``max_words`` (from
Settings) it is trimmed to exactly that many words and a ``system`` violation
event is logged; otherwise the text is returned unchanged.

Task 4.5 (issue #36) registers the skills as real Pydantic AI **tools**
(:mod:`~agent_debate.core.agents.tools`): :func:`debater_tools` and
:func:`controller_tools` return the two disjoint tool sets (each tool's argument is a
Pydantic input model, so a malformed payload is rejected at the tool boundary), wired
into :func:`create_debater` / :func:`create_controller` so each returned agent actually
carries its skills as callable tools.

The re-exports below are the subpackage's public surface.
"""

from __future__ import annotations

from agent_debate.core.agents.anchoring import (
    ANTI_CONCESSION_RULE,
    anchor_turn,
    build_side_anchor,
)
from agent_debate.core.agents.context import (
    CONTROLLER_IDENTITY,
    AgentContext,
    DebateContexts,
    Role,
    Turn,
    create_debate_contexts,
)
from agent_debate.core.agents.controller import create_controller
from agent_debate.core.agents.controller_prompts import (
    CONTROLLER_SKILLS,
    build_controller_system_prompt,
)
from agent_debate.core.agents.debater import (
    create_con_debater,
    create_debater,
    create_pro_debater,
)
from agent_debate.core.agents.prompts import DEBATER_SKILLS, build_debater_system_prompt
from agent_debate.core.agents.relay import (
    ADVERSARIAL_RELAY_TEMPLATE,
    build_adversarial_relay,
    relay_opponent_turn,
)
from agent_debate.core.agents.tools import controller_tools, debater_tools
from agent_debate.core.agents.word_limit import (
    WordLimitResult,
    count_words,
    enforce_word_limit,
)

__all__ = [
    "ADVERSARIAL_RELAY_TEMPLATE",
    "ANTI_CONCESSION_RULE",
    "CONTROLLER_IDENTITY",
    "CONTROLLER_SKILLS",
    "DEBATER_SKILLS",
    "AgentContext",
    "DebateContexts",
    "Role",
    "Turn",
    "WordLimitResult",
    "anchor_turn",
    "build_adversarial_relay",
    "build_controller_system_prompt",
    "build_debater_system_prompt",
    "build_side_anchor",
    "controller_tools",
    "count_words",
    "create_con_debater",
    "create_controller",
    "create_debate_contexts",
    "create_debater",
    "create_pro_debater",
    "debater_tools",
    "enforce_word_limit",
    "relay_opponent_turn",
]
