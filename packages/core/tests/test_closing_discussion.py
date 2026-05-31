"""Tests for the CLOSING DISCUSSION phase (issue #50, task 6.5, orchestration §3.3).

TDD-first: these assert the §3.3 contract before :func:`run_closing_discussion`
exists. After the main ``rounds``-round loop, a *freer* closing exchange runs —
each debater (Pro then Con) gives one closing statement per exchange — before
judgement. The closing turns are word-limited, logged as ``message`` events
tagged ``closing`` (round ``0``), and routed through the API gatekeeper; they are
stored in :attr:`DebateResult.closing_discussion`, kept SEPARATE from the main
``transcript`` (which still holds exactly ``rounds * 2`` turns).

Everything runs offline: agents use a pydantic-ai ``FunctionModel`` (no network,
no key); every model call routes through an injected (spy) gatekeeper; log
assertions read a ``tmp_path`` runs dir. Caps come from the config / a single
named constant, never hard-coded here.
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
from agent_debate.core.constants import CLOSING_EXCHANGES
from agent_debate.core.engine import run_debate_loop
from agent_debate.core.engine.closing import run_closing_discussion
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

_TOPIC = "Should remote work be the default for office jobs?"


def _config(*, rounds: int = 1, max_words: int = 50) -> DebateConfig:
    """A small config built from explicit settings (config-driven, no hard-coding)."""
    return DebateConfig.from_settings(Settings(rounds=rounds, max_words=max_words))


def _text_model(text: str) -> FunctionModel:
    """A model that always returns ``text`` regardless of the prompt."""

    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(content=text)])

    return FunctionModel(_fn)


def _models(*, pro: Model, con: Model) -> dict[object, Model]:
    """Per-agent model map (Pro/Con/Controller) — offline, no key."""
    return {DebateSide.PRO: pro, DebateSide.CON: con, "controller": TestModel()}


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


def test_loop_runs_closing_discussion_with_both_sides(tmp_path: Path) -> None:
    """After the main loop, ``closing_discussion`` holds a closing turn from each side."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=1)
    setup = setup_debate(
        _TOPIC, config, models=_models(pro=_text_model("pro close"), con=_text_model("con close"))
    )
    result = run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("c1", runs_dir), run_id="c1", runs_dir=runs_dir
    )
    assert result.closing_discussion, "expected a non-empty closing discussion"
    sides = {m.side for m in result.closing_discussion}
    assert sides == {DebateSide.PRO, DebateSide.CON}
    assert len(result.closing_discussion) == CLOSING_EXCHANGES * 2


def test_main_transcript_separate_from_closing(tmp_path: Path) -> None:
    """The main transcript still has exactly ``rounds * 2`` turns; closing is separate."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=2)
    setup = setup_debate(
        _TOPIC, config, models=_models(pro=_text_model("pro close"), con=_text_model("con close"))
    )
    result = run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("c2", runs_dir), run_id="c2", runs_dir=runs_dir
    )
    assert len(result.transcript) == config.rounds * 2
    assert all(m not in result.transcript for m in result.closing_discussion)


def test_closing_turns_respect_word_limit(tmp_path: Path) -> None:
    """An over-limit closing statement is trimmed to exactly ``max_words``."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=1, max_words=5)
    long_text = " ".join(f"w{i}" for i in range(20))
    setup = setup_debate(
        _TOPIC, config, models=_models(pro=_text_model(long_text), con=_text_model("con ok"))
    )
    result = run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("c3", runs_dir), run_id="c3", runs_dir=runs_dir
    )
    assert all(m.word_count <= config.max_words for m in result.closing_discussion)
    pro_close = next(m for m in result.closing_discussion if m.side is DebateSide.PRO)
    assert pro_close.word_count == 5


def test_closing_turns_logged_as_closing_messages(tmp_path: Path) -> None:
    """Each closing turn is logged as a ``message`` event tagged closing (round 0)."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=1)
    setup = setup_debate(
        _TOPIC, config, models=_models(pro=_text_model("pro close"), con=_text_model("con close"))
    )
    run_debate_loop(
        setup, config, gatekeeper=_gatekeeper("c4", runs_dir), run_id="c4", runs_dir=runs_dir
    )
    closing = [
        e
        for e in _events(runs_dir, "c4")
        if e["event_type"] == "message" and e["payload"].get("closing") is True
    ]
    assert len(closing) == CLOSING_EXCHANGES * 2
    assert all(e["round"] == 0 for e in closing)
    assert {e["agent"] for e in closing} == {"pro", "con"}


def test_closing_routes_through_gatekeeper(tmp_path: Path) -> None:
    """Every closing model call routes through the injected gatekeeper (no bypass)."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=1)
    spy = _gatekeeper("c5", runs_dir)
    setup = setup_debate(
        _TOPIC, config, models=_models(pro=_text_model("pro close"), con=_text_model("con close"))
    )
    closing = run_closing_discussion(setup, config, gatekeeper=spy, run_id="c5", runs_dir=runs_dir)
    assert len(closing) == CLOSING_EXCHANGES * 2
    # One execute() per closing turn: CLOSING_EXCHANGES * 2 sides, all gatekept.
    assert len(spy.calls) == CLOSING_EXCHANGES * 2
