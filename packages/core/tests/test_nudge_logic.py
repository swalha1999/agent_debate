"""Tests for the private-nudge logic (issue #61, task 8.2, anti-sycophancy §2.4/§4).

TDD-first: these assert the deepened §4 nudge contract before the wiring exists.
When ``assess_drift`` reports capture, the controller sends a PRIVATE correction
to that agent — injected into the captured agent's OWN context (so it sees the
correction before its next turn), NOT into the opponent's context and NOT into the
public transcript. The nudge is logged + streamed (the 6.6 event stream) and
recorded in ``DebateResult.nudges``, but **does not** count as a debate turn
(``is_debate_turn is False``); the 10-vs-10 message invariant is unaffected.

Everything runs offline: agents use a pydantic-ai ``FunctionModel`` (no network,
no key); model calls route through an injected :class:`ApiGatekeeper`; log
assertions read a ``tmp_path`` runs dir. The captured agent's drift reason names
its side, and the private correction names that side — both config-driven.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_debate.core import (
    ApiGatekeeper,
    DebateConfig,
    DebateSide,
    Settings,
    load_rate_limit_config,
    setup_debate,
)
from agent_debate.core.agents.context import AgentContext
from agent_debate.core.engine import run_debate_loop
from agent_debate.core.engine.drift import inject_nudge, run_drift_check
from agent_debate.core.skills import nudge
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, FunctionModel

_TOPIC = "Should remote work be the default for office jobs?"
_CONCEDE = "You're right, I concede the core point entirely."


def _config(*, rounds: int = 1, max_words: int = 50) -> DebateConfig:
    return DebateConfig.from_settings(Settings(rounds=rounds, max_words=max_words))


def _text_model(text: str) -> FunctionModel:
    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(content=text)])

    return FunctionModel(_fn)


def _models(*, pro: Model, con: Model) -> dict[object, Model]:
    return {DebateSide.PRO: pro, DebateSide.CON: con, "controller": _text_model("ok")}


def _events(runs_dir: Path, run_id: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (runs_dir / f"{run_id}.jsonl").read_text().splitlines()]


def _gatekeeper(run_id: str, runs_dir: Path) -> ApiGatekeeper:
    return ApiGatekeeper(load_rate_limit_config(), run_id=run_id, runs_dir=runs_dir)


def test_inject_nudge_appends_correction_to_captured_context_only() -> None:
    """``inject_nudge`` appends the correction as a user turn into the given context."""
    context = AgentContext(identity=DebateSide.PRO.value)
    correction = nudge(DebateSide.PRO, "Conceded the core claim.")

    injected = inject_nudge(context, correction)

    history = context.history()
    assert len(history) == 1
    assert history[0].role == "user"
    assert history[0].content == injected == correction.correction


def test_run_drift_check_injects_private_correction_into_agent_context(tmp_path: Path) -> None:
    """On capture the correction is injected into the captured agent's OWN context."""
    runs_dir = Path(str(tmp_path))
    context = AgentContext(identity=DebateSide.PRO.value)

    correction = run_drift_check(
        message=_CONCEDE,
        side=DebateSide.PRO,
        round_=1,
        run_id="n1",
        runs_dir=runs_dir,
        context=context,
    )

    assert correction is not None
    history = context.history()
    assert any(t.role == "user" and t.content == correction.correction for t in history)


def test_clean_message_does_not_inject_nudge(tmp_path: Path) -> None:
    """An on-side message produces no nudge and leaves the context untouched."""
    runs_dir = Path(str(tmp_path))
    context = AgentContext(identity=DebateSide.PRO.value)

    correction = run_drift_check(
        message="Remote work clearly raises productivity; here is the evidence.",
        side=DebateSide.PRO,
        round_=1,
        run_id="n2",
        runs_dir=runs_dir,
        context=context,
    )

    assert correction is None
    assert context.history() == ()


def test_loop_nudge_goes_to_captured_agent_not_opponent_or_transcript(tmp_path: Path) -> None:
    """The private nudge lands in the captured agent's context only — not Con's/transcript."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=1)
    setup = setup_debate(
        _TOPIC,
        config,
        models=_models(pro=_text_model(_CONCEDE), con=_text_model("con rebut")),
    )
    result = run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("n3", runs_dir), run_id="n3", runs_dir=runs_dir
    )

    assert result.nudges, "expected a nudge for the captured Pro"
    correction = result.nudges[0].correction
    pro_history = "\n".join(t.content for t in setup.contexts.pro.history())
    con_history = "\n".join(t.content for t in setup.contexts.con.history())
    assert correction in pro_history
    assert correction not in con_history
    assert all(correction != m.content for m in result.transcript)


def test_loop_nudge_is_logged_streamed_and_not_a_debate_turn(tmp_path: Path) -> None:
    """The nudge is logged + recorded, names the side, and never consumes a debate turn."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=1)
    setup = setup_debate(
        _TOPIC,
        config,
        models=_models(pro=_text_model(_CONCEDE), con=_text_model("con rebut")),
    )
    result = run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("n4", runs_dir), run_id="n4", runs_dir=runs_dir
    )

    assert all(n.is_debate_turn is False for n in result.nudges)
    assert result.nudges[0].target is DebateSide.PRO
    assert DebateSide.PRO.value in result.nudges[0].correction
    # 10-vs-10 invariant: the nudge does NOT add a debate turn.
    assert len([m for m in result.transcript if m.side is DebateSide.PRO]) == 1
    assert len([m for m in result.transcript if m.side is DebateSide.CON]) == 1
    nudge_events = [e for e in _events(runs_dir, "n4") if e["event_type"] == "nudge"]
    assert nudge_events, "expected a logged nudge event"
    assert nudge_events[0]["payload"]["target"] == DebateSide.PRO.value
