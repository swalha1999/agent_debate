"""Controller-as-relay-hub routing (issue #219, HW2 §8.3.7).

The debate must flow THROUGH the father: every message goes child → father →
child; the debaters never communicate directly. These tests drive the real engine
loop with offline models and pin that contract:

* the controller's forward step (:func:`~agent_debate.core.engine.forward.
  forward_to_opponent`) is invoked for EACH debater message before it reaches the
  opponent — asserted via a spy on the forward call AND the logged routing event;
* the opponent's context still receives the §5.6 adversarially-framed message
  (existing relay behaviour preserved — it must rebut, not echo);
* 5.4 context isolation holds — Con never sees Pro's RAW turn, only the
  controller-forwarded frame (and vice versa);
* the controller drift-check still runs after each turn.

Everything runs offline (a ``FunctionModel`` per agent, no network/key); model
calls route through an injected :class:`ApiGatekeeper`; log assertions read a
``tmp_path`` runs dir. Caps come from a :class:`DebateConfig`, never hard-coded.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from agent_debate.core import (
    ApiGatekeeper,
    DebateConfig,
    DebateSide,
    Settings,
    load_rate_limit_config,
    setup_debate,
)
from agent_debate.core.agents.relay import ADVERSARIAL_RELAY_TEMPLATE
from agent_debate.core.constants import LOOP_RELAY_EVENT_TAG
from agent_debate.core.engine import forward_to_opponent, run_debate_loop
from agent_debate.core.engine import loop as loop_module
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

_TOPIC = "Should remote work be the default for office jobs?"
_PRO_TEXT = "pro distinctive claim"
_CON_TEXT = "con distinctive rebuttal"


def _config(*, rounds: int = 2, max_words: int = 50) -> DebateConfig:
    return DebateConfig.from_settings(Settings(rounds=rounds, max_words=max_words))


def _text_model(text: str) -> FunctionModel:
    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(content=text)])

    return FunctionModel(_fn)


def _models(*, pro: Model, con: Model) -> dict[object, Model]:
    return {DebateSide.PRO: pro, DebateSide.CON: con, "controller": TestModel()}


def _gatekeeper(run_id: str, runs_dir: Path) -> ApiGatekeeper:
    return ApiGatekeeper(load_rate_limit_config(), run_id=run_id, runs_dir=runs_dir)


def _events(runs_dir: Path, run_id: str) -> list[dict[str, Any]]:
    path = runs_dir / run_id / f"{run_id}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


def _routing_events(runs_dir: Path, run_id: str) -> list[dict[str, Any]]:
    return [
        e
        for e in _events(runs_dir, run_id)
        if e["event_type"] == "system" and e["payload"].get("event") == LOOP_RELAY_EVENT_TAG
    ]


def _setup(run_id: str, runs_dir: Path, config: DebateConfig):  # type: ignore[no-untyped-def]
    return setup_debate(
        _TOPIC,
        config,
        models=_models(pro=_text_model(_PRO_TEXT), con=_text_model(_CON_TEXT)),
    )


def test_every_message_is_routed_through_the_controller(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Each debater message is handed to the controller's forward step (child→father→child)."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=2)
    setup = _setup("cr1", runs_dir, config)
    calls: list[tuple[str, str]] = []

    def _spy(*, message: str, from_side: DebateSide, to_side: DebateSide, **kwargs: Any) -> str:
        calls.append((from_side.value, to_side.value))
        return forward_to_opponent(message=message, from_side=from_side, to_side=to_side, **kwargs)

    monkeypatch.setattr(loop_module, "forward_to_opponent", _spy)
    run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("cr1", runs_dir), run_id="cr1", runs_dir=runs_dir
    )
    # Every produced main-loop message is forwarded through the father: 2 rounds ×
    # (Pro→Con then Con→Pro) = 4 forwards, alternating sender/receiver.
    assert calls == [
        ("pro", "con"),
        ("con", "pro"),
        ("pro", "con"),
        ("con", "pro"),
    ]


def test_routing_is_logged_as_demonstrable_evidence(tmp_path: Path) -> None:
    """Each forward logs a ``system`` routing event naming from/to sides (the evidence)."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=2)
    setup = _setup("cr2", runs_dir, config)
    run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("cr2", runs_dir), run_id="cr2", runs_dir=runs_dir
    )
    routed = _routing_events(runs_dir, "cr2")
    assert len(routed) == config.rounds * 2
    assert all(e["agent"] == "controller" for e in routed), "the father owns the relay"
    assert [(e["payload"]["from"], e["payload"]["to"]) for e in routed] == [
        ("pro", "con"),
        ("con", "pro"),
        ("pro", "con"),
        ("con", "pro"),
    ]


def test_opponent_receives_framed_message_via_controller(tmp_path: Path) -> None:
    """The opponent's context still gets the §5.6 adversarial frame the controller forwarded."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=1)
    setup = _setup("cr3", runs_dir, config)
    run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("cr3", runs_dir), run_id="cr3", runs_dir=runs_dir
    )
    relay_lead = ADVERSARIAL_RELAY_TEMPLATE.split("{message}")[0]
    con_history = "\n".join(t.content for t in setup.contexts.con.history())
    # Con rebuts Pro's forwarded message: the frame + Pro's content are present.
    assert relay_lead in con_history
    assert _PRO_TEXT in con_history


def test_context_isolation_only_framed_relay_crosses(tmp_path: Path) -> None:
    """Con never sees Pro's raw turn — only the controller-forwarded FRAMED relay."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=1)
    setup = _setup("cr4", runs_dir, config)
    run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("cr4", runs_dir), run_id="cr4", runs_dir=runs_dir
    )
    relay_lead = ADVERSARIAL_RELAY_TEMPLATE.split("{message}")[0]
    for turn in setup.contexts.con.history():
        if _PRO_TEXT in turn.content:
            # Pro's content only ever appears wrapped in the adversarial frame —
            # never as a bare/raw turn echoed from Pro's own context.
            assert relay_lead in turn.content
            assert turn.role == "user"


def test_drift_check_still_runs_after_each_turn(tmp_path: Path) -> None:
    """Routing through the father does not disturb the controller's drift-check + nudge."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=1)
    setup = setup_debate(
        _TOPIC,
        config,
        models=_models(pro=_text_model("You're right, I concede."), con=_text_model(_CON_TEXT)),
    )
    result = run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("cr5", runs_dir), run_id="cr5", runs_dir=runs_dir
    )
    assert result.nudges, "the conceding Pro is still drift-checked + nudged"
    assert result.nudges[0].target is DebateSide.PRO
    nudge_events = [e for e in _events(runs_dir, "cr5") if e["event_type"] == "nudge"]
    assert nudge_events, "drift nudge still logged after the controller-relay refactor"
