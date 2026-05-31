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
  the PRO agent, over a side-parameterizable :func:`create_debater` seam the Con debater
  (task 5.2) reuses.

The re-exports below are the subpackage's public surface.
"""

from __future__ import annotations

from agent_debate.core.agents.debater import create_debater, create_pro_debater
from agent_debate.core.agents.prompts import DEBATER_SKILLS, build_debater_system_prompt

__all__ = [
    "DEBATER_SKILLS",
    "build_debater_system_prompt",
    "create_debater",
    "create_pro_debater",
]
