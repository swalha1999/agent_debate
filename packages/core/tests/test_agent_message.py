"""Structured JSON inter-agent message envelope (issue #220, HW2 §8.3.8).

HW2 §8.3.8 asks inter-agent / IPC communication to use a structured **JSON**
format (monitorable, token-saving). The agent-to-agent hop is the controller's
forward step (:func:`~agent_debate.core.engine.forward.forward_to_opponent`).
These tests pin that:

* the hop is represented as a typed :class:`~agent_debate.core.engine.message.
  AgentMessage` carrying ``round``/``from_side``/``to_side``/``type``/``content``
  and it round-trips losslessly through JSON (``model_dump_json`` → parse → equal);
* the controller's forward step LOGS that JSON envelope on the routing event for
  every hop (the structured fields appear in the captured payload), without
  breaking the existing routing-event shape;
* the text injected into the OPPONENT is still the legible §5.6 adversarial frame
  derived from ``content`` (debate quality / prompt legibility preserved);
* 5.4 isolation is unchanged — the opponent only ever sees the framed relay.

Everything runs offline (a ``FunctionModel`` per agent, no network/key); model
calls route through an injected :class:`ApiGatekeeper`; log assertions read a
``tmp_path`` runs dir. Caps come from a :class:`DebateConfig`, never hard-coded.
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
from agent_debate.core.agents.relay import ADVERSARIAL_RELAY_TEMPLATE, build_adversarial_relay
from agent_debate.core.constants import LOOP_RELAY_ENVELOPE_KEY, LOOP_RELAY_EVENT_TAG
from agent_debate.core.engine import forward_to_opponent, run_debate_loop
from agent_debate.core.engine.message import AgentMessage
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
    path = runs_dir / f"{run_id}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


def _routing_events(runs_dir: Path, run_id: str) -> list[dict[str, Any]]:
    return [
        e
        for e in _events(runs_dir, run_id)
        if e["event_type"] == "system" and e["payload"].get("event") == LOOP_RELAY_EVENT_TAG
    ]


def _setup(config: DebateConfig):  # type: ignore[no-untyped-def]
    return setup_debate(
        _TOPIC,
        config,
        models=_models(pro=_text_model(_PRO_TEXT), con=_text_model(_CON_TEXT)),
    )


def test_agent_message_has_structured_fields() -> None:
    """The envelope carries round / from-side / to-side / type / content (§8.3.8)."""
    msg = AgentMessage(
        round=3,
        from_side=DebateSide.PRO,
        to_side=DebateSide.CON,
        content=_PRO_TEXT,
    )
    assert msg.round == 3
    assert msg.from_side is DebateSide.PRO
    assert msg.to_side is DebateSide.CON
    assert msg.content == _PRO_TEXT
    # ``type`` defaults to the relay kind so every hop is self-describing.
    assert isinstance(msg.type, str) and msg.type


def test_agent_message_round_trips_through_json() -> None:
    """``model_dump_json`` → parse → :class:`AgentMessage` reconstructs an equal model."""
    msg = AgentMessage(
        round=2,
        from_side=DebateSide.CON,
        to_side=DebateSide.PRO,
        content=_CON_TEXT,
    )
    raw = msg.model_dump_json()
    # It is genuine JSON (monitorable), and re-parsing yields an equal envelope.
    parsed = json.loads(raw)
    assert parsed["from_side"] == "con"
    assert parsed["to_side"] == "pro"
    assert parsed["round"] == 2
    assert parsed["content"] == _CON_TEXT
    assert AgentMessage.model_validate_json(raw) == msg


def test_agent_message_renders_legible_adversarial_frame() -> None:
    """Rendering the envelope yields the SAME legible §5.6 frame the model receives."""
    msg = AgentMessage(
        round=1,
        from_side=DebateSide.PRO,
        to_side=DebateSide.CON,
        content=_PRO_TEXT,
    )
    assert msg.render() == build_adversarial_relay(_PRO_TEXT)


def test_forward_logs_json_envelope_for_each_hop(tmp_path: Path) -> None:
    """Each controller forward logs the structured JSON envelope on its routing event."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=2)
    setup = _setup(config)
    run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("am1", runs_dir), run_id="am1", runs_dir=runs_dir
    )
    routed = _routing_events(runs_dir, "am1")
    assert len(routed) == config.rounds * 2
    for event, (frm, to) in zip(
        routed, [("pro", "con"), ("con", "pro"), ("pro", "con"), ("con", "pro")], strict=True
    ):
        envelope = event["payload"][LOOP_RELAY_ENVELOPE_KEY]
        # The structured JSON envelope is present and self-describing per hop, and
        # re-hydrates into an equal typed AgentMessage (monitorable + lossless).
        assert envelope["from_side"] == frm
        assert envelope["to_side"] == to
        assert envelope["round"] == event["round"]
        assert AgentMessage.model_validate(envelope).from_side.value == frm
    # The flat from/to fields stay for back-compat with the #219 routing contract.
    assert routed[0]["payload"]["from"] == "pro"
    assert routed[0]["payload"]["to"] == "con"


def test_forward_returns_legible_frame_derived_from_content(tmp_path: Path) -> None:
    """The opponent still gets the legible framed relay built from the envelope content."""
    runs_dir = Path(str(tmp_path))
    framed = forward_to_opponent(
        message=_PRO_TEXT,
        from_side=DebateSide.PRO,
        to_side=DebateSide.CON,
        round_=1,
        run_id="am2",
        runs_dir=runs_dir,
    )
    assert framed == build_adversarial_relay(_PRO_TEXT, run_id="am2")


def test_opponent_context_receives_legible_frame_not_raw(tmp_path: Path) -> None:
    """Debate quality preserved: Con sees the legible frame derived from Pro's content."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=1)
    setup = _setup(config)
    run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("am3", runs_dir), run_id="am3", runs_dir=runs_dir
    )
    relay_lead = ADVERSARIAL_RELAY_TEMPLATE.split("{message}")[0]
    con_history = "\n".join(t.content for t in setup.contexts.con.history())
    assert relay_lead in con_history
    assert _PRO_TEXT in con_history
