"""Tests for the main debate LOOP (issue #48, task 6.3, orchestration §3.2).

TDD-first: these assert the §3.2 loop contract before :func:`run_debate_loop`
exists. The loop runs ``ROUNDS`` rounds alternating Pro turn → controller
drift-check (+nudge if captured) → Con turn (must rebut Pro) → controller
drift-check (+nudge), producing exactly ``ROUNDS`` Pro + ``ROUNDS`` Con messages
(each ≤ ``max_words``) and logging every message / nudge.

Everything runs offline: agents use a pydantic-ai ``FunctionModel`` /
``TestModel`` (no network, no key); every model call routes through an injected
(spy) :class:`ApiGatekeeper`; log assertions read a ``tmp_path`` runs dir. Caps
(rounds, max_words) come from the :class:`DebateConfig`, never hard-coded here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_debate.core import (
    ApiGatekeeper,
    DebateConfig,
    DebateResult,
    DebateSide,
    Settings,
    load_rate_limit_config,
    setup_debate,
)
from agent_debate.core.engine import run_debate_loop
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

_TOPIC = "Should remote work be the default for office jobs?"


def _config(*, rounds: int = 2, max_words: int = 50) -> DebateConfig:
    """A small config built from explicit settings (config-driven, no hard-coding)."""
    return DebateConfig.from_settings(Settings(rounds=rounds, max_words=max_words))


def _text_model(text: str) -> FunctionModel:
    """A model that always returns ``text`` regardless of the prompt."""

    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(content=text)])

    return FunctionModel(_fn)


def _models(*, pro: Model, con: Model, controller: Model | None = None) -> dict[object, Model]:
    """Per-agent model map (Pro/Con/Controller) — offline, no key."""
    return {
        DebateSide.PRO: pro,
        DebateSide.CON: con,
        "controller": controller or TestModel(),
    }


class _SpyGatekeeper:
    """Wraps a real :class:`ApiGatekeeper`, counting :meth:`execute` calls."""

    def __init__(self, inner: ApiGatekeeper) -> None:
        self._inner = inner
        self.calls: list[dict[str, object]] = []

    def execute(self, api_call, *args, service="default", **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append({"service": service})
        return self._inner.execute(api_call, *args, service=service, **kwargs)


def _gatekeeper(run_id: str, runs_dir: Path) -> _SpyGatekeeper:
    return _SpyGatekeeper(ApiGatekeeper(load_rate_limit_config(), run_id=run_id, runs_dir=runs_dir))


def _events(runs_dir: Path, run_id: str) -> list[dict[str, Any]]:
    path = runs_dir / f"{run_id}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_loop_produces_rounds_pro_and_con_messages_alternating(tmp_path: Path) -> None:
    """The transcript holds exactly ``rounds`` Pro + ``rounds`` Con turns, alternating."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=2)
    setup = setup_debate(
        _TOPIC, config, models=_models(pro=_text_model("pro point"), con=_text_model("con rebut"))
    )
    result = run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("r1", runs_dir), run_id="r1", runs_dir=runs_dir
    )
    assert isinstance(result, DebateResult)
    pro = [m for m in result.transcript if m.side is DebateSide.PRO]
    con = [m for m in result.transcript if m.side is DebateSide.CON]
    assert len(pro) == 2
    assert len(con) == 2
    sides = [m.side for m in result.transcript]
    assert sides == [DebateSide.PRO, DebateSide.CON, DebateSide.PRO, DebateSide.CON]
    rounds = [m.round for m in result.transcript]
    assert rounds == [1, 1, 2, 2]


def test_loop_trims_over_limit_message(tmp_path: Path) -> None:
    """A message over ``max_words`` is trimmed to exactly the limit + a violation logged."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=1, max_words=5)
    long_text = " ".join(f"w{i}" for i in range(20))
    setup = setup_debate(
        _TOPIC, config, models=_models(pro=_text_model(long_text), con=_text_model("con ok"))
    )
    result = run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("r2", runs_dir), run_id="r2", runs_dir=runs_dir
    )
    pro = next(m for m in result.transcript if m.side is DebateSide.PRO)
    assert pro.word_count == 5
    assert all(m.word_count <= config.max_words for m in result.transcript)
    violations = [
        e for e in _events(runs_dir, "r2") if e["payload"].get("violation") == "word_limit"
    ]
    assert violations, "expected a word-limit violation event"


def test_loop_conceding_pro_triggers_drift_nudge(tmp_path: Path) -> None:
    """A conceding Pro message is captured → a nudge is recorded (not a debate turn)."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=1)
    setup = setup_debate(
        _TOPIC,
        config,
        models=_models(pro=_text_model("You're right, I concede."), con=_text_model("con rebut")),
    )
    result = run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("r3", runs_dir), run_id="r3", runs_dir=runs_dir
    )
    assert result.nudges, "expected a nudge for the captured Pro"
    assert result.nudges[0].target is DebateSide.PRO
    assert all(n.is_debate_turn is False for n in result.nudges)
    # The nudge does NOT consume a debate turn: still exactly 1 Pro + 1 Con.
    assert len([m for m in result.transcript if m.side is DebateSide.PRO]) == 1
    assert len([m for m in result.transcript if m.side is DebateSide.CON]) == 1
    nudge_events = [e for e in _events(runs_dir, "r3") if e["event_type"] == "nudge"]
    assert nudge_events, "expected a logged nudge event"


def test_loop_logs_every_message_in_order(tmp_path: Path) -> None:
    """Every Pro/Con turn is logged as a ``message`` event, ordered by round/side."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=2)
    setup = setup_debate(
        _TOPIC, config, models=_models(pro=_text_model("pro point"), con=_text_model("con rebut"))
    )
    run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("r4", runs_dir), run_id="r4", runs_dir=runs_dir
    )
    messages = [e for e in _events(runs_dir, "r4") if e["event_type"] == "message"]
    assert len(messages) == 4
    assert [(m["round"], m["agent"]) for m in messages] == [
        (1, "pro"),
        (1, "con"),
        (2, "pro"),
        (2, "con"),
    ]


def test_loop_routes_every_model_call_through_gatekeeper(tmp_path: Path) -> None:
    """Each debate turn's model call routes through the injected gatekeeper."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=2)
    spy = _gatekeeper("r5", runs_dir)
    setup = setup_debate(
        _TOPIC, config, models=_models(pro=_text_model("pro point"), con=_text_model("con rebut"))
    )
    run_debate_loop(setup, config, gatekeeper=spy, run_id="r5", runs_dir=runs_dir)
    # One execute() per debater turn: rounds * 2 sides.
    assert len(spy.calls) == config.rounds * 2


def test_loop_default_gatekeeper_when_not_injected(tmp_path: Path) -> None:
    """Absent an injected gatekeeper, the loop builds one from the rate-limit config."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=1)
    setup = setup_debate(
        _TOPIC, config, models=_models(pro=_text_model("pro point"), con=_text_model("con rebut"))
    )
    result = run_debate_loop(setup, config, run_id="r6", runs_dir=runs_dir)
    assert len([m for m in result.transcript if m.side is DebateSide.PRO]) == 1
    assert len([m for m in result.transcript if m.side is DebateSide.CON]) == 1


def test_loop_con_rebuts_pro_via_relay(tmp_path: Path) -> None:
    """Con's context receives Pro's latest message framed adversarially (must rebut)."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=1)
    setup = setup_debate(
        _TOPIC,
        config,
        models=_models(pro=_text_model("pro distinctive claim"), con=_text_model("con rebut")),
    )
    run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("r7", runs_dir), run_id="r7", runs_dir=runs_dir
    )
    con_history = "\n".join(t.content for t in setup.contexts.con.history())
    assert "pro distinctive claim" in con_history
    assert "Rebut it" in con_history
