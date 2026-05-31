"""Re-export shim for the Epic-6 engine surface (orchestration sub-PRD §2).

The :mod:`agent_debate.core` hub aggregates every subpackage's public names and
already sits at the 150-code-line guideline (PRD §3.2). Rather than compress the
hub, the engine re-export group is factored out here and pulled into ``__init__``
with a single ``from ._engine_public import *`` (split, not compress) — mirroring
:mod:`agent_debate.core._agents_public`. This module re-exports the
:mod:`agent_debate.core.engine` public surface verbatim — it adds no behaviour.
"""

from __future__ import annotations

from agent_debate.core.engine import (
    CostTotals,
    DebateConfig,
    DebateMessage,
    DebateResult,
    DebateSetup,
    Gatekeeper,
    SetupModels,
    ToolCallRecord,
    UsageBreakdown,
    run_debate_loop,
    setup_debate,
)

__all__ = [
    "CostTotals",
    "DebateConfig",
    "DebateMessage",
    "DebateResult",
    "DebateSetup",
    "Gatekeeper",
    "SetupModels",
    "ToolCallRecord",
    "UsageBreakdown",
    "run_debate_loop",
    "setup_debate",
]
