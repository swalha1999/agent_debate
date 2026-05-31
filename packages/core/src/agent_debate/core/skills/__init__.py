"""Agent skills subpackage — the named tools each agent exposes (Epic 4).

PRD §5.2: each debater is a Pydantic AI ``Agent`` whose system prompt names the
**skills (tools)** it can call. This subpackage holds those skills and their
validated input/output models, mirroring the ``search``/``gatekeeper`` layout.

Task 4.2 ships the first skill, :func:`build_argument`, which *structures* a
persuasive argument or rebuttal for a debater's assigned side
(:class:`ArgumentRequest` → :class:`Argument`, with :class:`DebateSide`). Task 4.3
adds :func:`analyze_opponent_argument`, which *dissects* the opponent's last
message into an :class:`OpponentAnalysis` (key claims, weaknesses, a prioritised
``rebuttal_target`` that feeds ``build_argument``'s ``opponent_point``). Task 4.4
adds the **controller** skills (PRD §5.3) — :func:`assess_drift` (capture/drift
classification → :class:`DriftAssessment`), :func:`nudge` (a private
:class:`NudgeMessage` correction that never counts as a debate turn), and
:func:`render_verdict` (a debate-derived :class:`Verdict` that never reveals the
controller's own stance). All are pure, deterministic structuring helpers — no
LLM/network call — so the API gatekeeper (Epic 13) does not apply. Wiring these
functions as real Pydantic AI tools is task 4.5; here the validated-input functions
are tool-ready. The re-exports below are the subpackage's public surface.
"""

from __future__ import annotations

from agent_debate.core.skills.analyze_opponent import analyze_opponent_argument
from agent_debate.core.skills.build_argument import build_argument
from agent_debate.core.skills.controller import assess_drift, nudge, render_verdict
from agent_debate.core.skills.models import (
    Argument,
    ArgumentRequest,
    DebateSide,
    DriftAssessment,
    DriftRequest,
    NudgeMessage,
    NudgeRequest,
    OpponentAnalysis,
    OpponentAnalysisRequest,
    TranscriptTurn,
    Verdict,
    VerdictRequest,
    WebSearchInput,
)
from agent_debate.core.skills.web_search import web_search

__all__ = [
    "Argument",
    "ArgumentRequest",
    "DebateSide",
    "DriftAssessment",
    "DriftRequest",
    "NudgeMessage",
    "NudgeRequest",
    "OpponentAnalysis",
    "OpponentAnalysisRequest",
    "TranscriptTurn",
    "Verdict",
    "VerdictRequest",
    "WebSearchInput",
    "analyze_opponent_argument",
    "assess_drift",
    "build_argument",
    "nudge",
    "render_verdict",
    "web_search",
]
