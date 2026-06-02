"""Reusable staged-drift fixtures (anti-sycophancy §4 acceptance, issue #63).

Kept separate from ``test_staged_drift.py`` so each file stays under the 150-line
guideline (PRD §3.2). Everything is offline: agents use a pydantic-ai
``FunctionModel`` (no network, no key); model calls route through an injected
:class:`~agent_debate.core.ApiGatekeeper`; the JSONL sink lives under ``tmp_path``.

The headline helper, :func:`drifting_model`, builds a debater whose ``round``-th
turn deterministically PARROTS/CONCEDES to the opponent (a clearly-conceding line
drawn from the §3 concede lexicon) while every other turn stays on-side. Driving
that message through the real engine drift path forces :func:`assess_drift` to flag
capture and the controller to nudge the agent back — the §4 staged-drift fixture.
Reuse it from future tests by importing :func:`drifting_model` / :func:`staged_run`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_debate.core import (
    ApiGatekeeper,
    DebateConfig,
    DebateEngine,
    DebateResult,
    DebateSide,
    Settings,
    load_rate_limit_config,
)
from agent_debate.core.skills._drift_constants import DRIFT_CONCEDE_PHRASES
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

TOPIC = "Should remote work be the default for office jobs?"

#: A clearly-conceding line built from the §3 concede lexicon so the deterministic
#: detector flags capture (no literal duplication — sourced from the constants).
CONCEDING_LINE = f"You're right, {DRIFT_CONCEDE_PHRASES[0]} the core claim; the opponent is correct"

#: The gatekeeper (Epic 13) logs its own infra events under its bound run_id — not
#: part of the debate event stream; filtered out when reading the JSONL.
GATEKEEPER_AGENT = "gatekeeper"


def config(*, rounds: int, max_words: int = 80) -> DebateConfig:
    """A config built from explicit settings (config-driven, no hard-coding)."""
    return DebateConfig.from_settings(Settings(rounds=rounds, max_words=max_words))


def _on_side(side: DebateSide) -> str:
    """A plain on-side line for ``side`` that fires no drift signal."""
    return f"The {side.value} side stands; the resolution must be defended on its merits."


def drifting_model(side: DebateSide, *, concede_round: int) -> FunctionModel:
    """A debater that PARROTS/CONCEDES on its ``concede_round`` turn, else on-side.

    The model counts the turns it is asked to produce (each generation is one turn)
    and emits :data:`CONCEDING_LINE` on the ``concede_round``-th turn so the staged
    drift lands at a deterministic, known round; all other turns stay on-side.

    Args:
        side: The debater's assigned stance (drives the on-side filler text).
        concede_round: 1-based turn index on which to emit the conceding line.

    Returns:
        A :class:`FunctionModel` driving deterministic staged drift, no network.
    """
    state = {"turn": 0}

    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        state["turn"] += 1
        text = CONCEDING_LINE if state["turn"] == concede_round else _on_side(side)
        return ModelResponse(parts=[TextPart(content=text)])

    return FunctionModel(_fn)


def _last_user_text(messages: list[ModelMessage]) -> str:
    """Concatenate the text parts of the last ``ModelRequest`` (the live prompt)."""
    for message in reversed(messages):
        if isinstance(message, ModelRequest):
            return " ".join(
                getattr(part, "content", "")
                for part in message.parts
                if isinstance(getattr(part, "content", None), str)
            )
    return ""


def capturing_drifting_model(
    side: DebateSide, *, concede_round: int, seen: list[str]
) -> FunctionModel:
    """Like :func:`drifting_model` but records each prompt into ``seen``.

    Lets a test assert the private nudge is injected into the captured agent's OWN
    context (it appears in a later prompt) rather than the public transcript.
    """
    state = {"turn": 0}

    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append(_last_user_text(messages))
        state["turn"] += 1
        text = CONCEDING_LINE if state["turn"] == concede_round else _on_side(side)
        return ModelResponse(parts=[TextPart(content=text)])

    return FunctionModel(_fn)


def models(*, pro: Model, con: Model) -> dict[object, Model]:
    """Per-agent model map (Pro/Con/Controller) — offline, no key."""
    return {DebateSide.PRO: pro, DebateSide.CON: con, "controller": TestModel()}


def staged_run(
    run_id: str,
    runs_dir: Path,
    *,
    pro: Model,
    con: Model,
    rounds: int = 2,
) -> DebateResult:
    """Run a full offline debate with the given staged models, through the SDK."""
    cfg = config(rounds=rounds)
    keeper = ApiGatekeeper(load_rate_limit_config(), run_id=run_id, runs_dir=runs_dir)
    engine = DebateEngine(
        cfg, models=models(pro=pro, con=con), gatekeeper=keeper, runs_dir=runs_dir
    )
    return engine.run(TOPIC, run_id=run_id)


def nudge_events(runs_dir: Path, run_id: str) -> list[dict[str, Any]]:
    """Read the run's JSONL log and return only the ``nudge`` events."""
    path = runs_dir / run_id / f"{run_id}.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    return [e for e in events if e["agent"] != GATEKEEPER_AGENT and e["event_type"] == "nudge"]
