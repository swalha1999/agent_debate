"""Agent skills subpackage — the named tools each agent exposes (Epic 4).

PRD §5.2: each debater is a Pydantic AI ``Agent`` whose system prompt names the
**skills (tools)** it can call. This subpackage holds those skills and their
validated input/output models, mirroring the ``search``/``gatekeeper`` layout.

Task 4.2 ships the first skill, :func:`build_argument`, which *structures* a
persuasive argument or rebuttal for a debater's assigned side
(:class:`ArgumentRequest` → :class:`Argument`, with :class:`DebateSide`). It is a
pure, deterministic structuring helper — no LLM/network call — so the API
gatekeeper (Epic 13) does not apply. Wiring these functions as real Pydantic AI
tools is task 4.5; here the validated-input function is tool-ready. The
re-exports below are the subpackage's public surface.
"""

from __future__ import annotations

from agent_debate.core.skills.build_argument import build_argument
from agent_debate.core.skills.models import Argument, ArgumentRequest, DebateSide

__all__ = ["Argument", "ArgumentRequest", "DebateSide", "build_argument"]
