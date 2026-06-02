"""Shared offline fixtures for the PRD §11 acceptance suite (TASKS.md 12.1, issue #81).

Kept separate from ``test_acceptance_criteria.py`` so each file stays under the
150-line guideline (PRD §3.2). Everything here is offline: agents use a
pydantic-ai ``FunctionModel`` (no network, no key); model calls route through an
injected :class:`~agent_debate.core.ApiGatekeeper`; the JSONL sink lives under
``tmp_path``. The repo-root locator powers the hygiene meta-criteria (no secrets,
≤150 lines, sub-PRDs present, runs committed) that PRD §11 also lists.
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
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

#: A debate topic with two clearly opposable sides (drives the engine offline).
TOPIC = "Should remote work be the default for office jobs?"

#: Repo root — ``packages/core/tests`` is three parents below it. Used by the
#: hygiene meta-criteria so each path is resolved once, never hard-coded inline.
REPO_ROOT = Path(__file__).resolve().parents[3]

#: The gatekeeper (Epic 13) logs its own infra events under its bound run_id —
#: not part of the debate event stream; filtered out when reading the JSONL.
GATEKEEPER_AGENT = "gatekeeper"


def config(*, rounds: int = 10, max_words: int = 150) -> DebateConfig:
    """A config built from explicit settings (config-driven, no hard-coding)."""
    return DebateConfig.from_settings(Settings(rounds=rounds, max_words=max_words))


def rebutting_model(text: str) -> FunctionModel:
    """A debater that always replies ``text`` (a clearly rebutting line), offline."""

    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(content=text)])

    return FunctionModel(_fn)


def models(*, pro: Model, con: Model) -> dict[object, Model]:
    """Per-agent model map (Pro/Con/Controller) — offline, no key."""
    return {DebateSide.PRO: pro, DebateSide.CON: con, "controller": TestModel()}


def run_engine(
    run_id: str,
    runs_dir: Path,
    *,
    pro: Model,
    con: Model,
    rounds: int = 10,
    max_words: int = 150,
) -> DebateResult:
    """Run a full offline debate through the public SDK with a real gatekeeper."""
    cfg = config(rounds=rounds, max_words=max_words)
    keeper = ApiGatekeeper(load_rate_limit_config(), run_id=run_id, runs_dir=runs_dir)
    engine = DebateEngine(
        cfg, models=models(pro=pro, con=con), gatekeeper=keeper, runs_dir=runs_dir
    )
    return engine.run(TOPIC, run_id=run_id)


def logged_events(runs_dir: Path, run_id: str) -> list[dict[str, Any]]:
    """Read the run's JSONL log, excluding the gatekeeper's own infra events."""
    path = runs_dir / run_id / f"{run_id}.jsonl"
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return [e for e in events if e["agent"] != GATEKEEPER_AGENT]
