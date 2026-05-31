"""Debate orchestration engine subpackage (Epic 6, sub-PRD ``debate-orchestration``).

PRD §5.1 / the orchestration sub-PRD §2 define the engine that runs a full
Pro-vs-Con debate: it takes a :class:`DebateConfig` (+ topic) and produces a
:class:`DebateResult`. Task 6.1 ships the **typed models only** — the input
config and the output result (transcript, tool calls, nudges, closing discussion,
verdict, token/cost/latency totals) — building clean seams for the loop, timeout
wrapper, closing discussion, event streaming and SDK entrypoint that follow
(tasks 6.2+). The re-exports below are the subpackage's public surface.
"""

from __future__ import annotations

from agent_debate.core.engine.gatekeeper_proto import Gatekeeper
from agent_debate.core.engine.loop import run_debate_loop
from agent_debate.core.engine.models import DebateConfig
from agent_debate.core.engine.result import (
    CostTotals,
    DebateMessage,
    DebateResult,
    ToolCallRecord,
)
from agent_debate.core.engine.setup import DebateSetup, SetupModels, setup_debate

__all__ = [
    "CostTotals",
    "DebateConfig",
    "DebateMessage",
    "DebateResult",
    "DebateSetup",
    "Gatekeeper",
    "SetupModels",
    "ToolCallRecord",
    "run_debate_loop",
    "setup_debate",
]
