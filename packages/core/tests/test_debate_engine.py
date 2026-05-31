"""Tests for the public SDK entrypoint — :class:`DebateEngine` (issue #53, 6.8).

TDD-first: these assert the §6 SDK surface contract before
:class:`~agent_debate.core.engine.sdk.DebateEngine` exists. ``DebateEngine`` is
THE library facade other packages (CLI/API/UI) drive: ``DebateEngine(config)
.run(topic) -> DebateResult`` plus a streaming variant ``.stream(topic)`` that
yields ordered, typed events live then the final :class:`DebateResult`.

Everything runs offline: agents use a pydantic-ai ``FunctionModel`` (no network,
no key); model calls route through an injected (spy) gatekeeper or the engine's
own config-driven default; log/JSONL helpers read a ``tmp_path`` runs dir. Caps
(rounds, max_words) come from a :class:`DebateConfig`, never hard-coded here.
"""

from __future__ import annotations

from pathlib import Path

from _event_stream_helpers import (
    TOPIC,
    config,
    key,
    logged_events,
    models,
    spy_gatekeeper,
    text_model,
)
from agent_debate.core import DebateConfig, DebateEngine, DebateResult, DebateSide
from agent_debate.core.constants import CLOSING_EXCHANGES
from agent_debate.core.engine import Gatekeeper, SetupModels
from agent_debate.log import EVENT_TYPES, LogEvent


def _models() -> SetupModels:
    return models(pro=text_model("pro point"), con=text_model("con rebut"))


def test_public_import_path_works() -> None:
    """The documented SDK import path resolves to the facade class."""
    from agent_debate.core import DebateEngine as ImportedEngine

    assert ImportedEngine is DebateEngine


def test_run_returns_debate_result_with_full_transcript(tmp_path: Path) -> None:
    """``run`` returns a DebateResult with rounds*2 turns, closing + totals."""
    runs_dir = Path(str(tmp_path))
    cfg = config(rounds=2)
    engine = DebateEngine(
        cfg,
        models=_models(),
        gatekeeper=spy_gatekeeper("e1", runs_dir),
        runs_dir=runs_dir,
    )
    result = engine.run(TOPIC, run_id="e1")
    assert isinstance(result, DebateResult)
    assert result.topic == TOPIC
    assert len([m for m in result.transcript if m.side is DebateSide.PRO]) == 2
    assert len([m for m in result.transcript if m.side is DebateSide.CON]) == 2
    assert len(result.closing_discussion) == CLOSING_EXCHANGES * 2
    assert result.totals.total_tokens >= 0


def test_run_generates_run_id_when_absent(tmp_path: Path) -> None:
    """Absent an explicit run_id, ``run`` mints one (uuid4) and still completes."""
    runs_dir = Path(str(tmp_path))
    cfg = config(rounds=1)
    engine = DebateEngine(
        cfg, models=_models(), gatekeeper=spy_gatekeeper("e2", runs_dir), runs_dir=runs_dir
    )
    result = engine.run(TOPIC)
    assert isinstance(result, DebateResult)
    assert len([m for m in result.transcript if m.side is DebateSide.PRO]) == 1


def test_run_routes_model_calls_through_gatekeeper(tmp_path: Path) -> None:
    """The held gatekeeper is used — every model call routes through it (no bypass)."""
    runs_dir = Path(str(tmp_path))
    cfg = config(rounds=2)

    class _Spy:
        def __init__(self, inner: Gatekeeper) -> None:
            self._inner = inner
            self.calls = 0

        def execute(self, api_call, *args, service="default", **kwargs):  # type: ignore[no-untyped-def]
            self.calls += 1
            return self._inner.execute(api_call, *args, service=service, **kwargs)

    spy = _Spy(spy_gatekeeper("e3", runs_dir))
    engine = DebateEngine(cfg, models=_models(), gatekeeper=spy, runs_dir=runs_dir)
    engine.run(TOPIC, run_id="e3")
    assert spy.calls == cfg.rounds * 2 + CLOSING_EXCHANGES * 2


def test_config_defaults_come_from_settings(tmp_path: Path) -> None:
    """``config=None`` builds the config from Settings via DebateConfig.from_settings."""
    runs_dir = Path(str(tmp_path))
    engine = DebateEngine(
        models=_models(), gatekeeper=spy_gatekeeper("e4", runs_dir), runs_dir=runs_dir
    )
    assert isinstance(engine.config, DebateConfig)
    assert engine.config.rounds == engine.settings.rounds
    assert engine.config.max_words == engine.settings.max_words


def test_stream_yields_ordered_events_then_result(tmp_path: Path) -> None:
    """``stream`` yields typed events live in order; the final item carries the result."""
    runs_dir = Path(str(tmp_path))
    cfg = config(rounds=1)
    engine = DebateEngine(
        cfg, models=_models(), gatekeeper=spy_gatekeeper("e5", runs_dir), runs_dir=runs_dir
    )
    events: list[LogEvent] = []
    result: DebateResult | None = None
    for item in engine.stream(TOPIC, run_id="e5"):
        if isinstance(item, LogEvent):
            events.append(item)
        else:
            result = item
    assert events, "stream should yield events"
    assert all(e.event_type in EVENT_TYPES for e in events)
    assert isinstance(result, DebateResult)
    assert [key(e) for e in events] == [key(e) for e in logged_events(runs_dir, "e5")]


def test_default_gatekeeper_is_config_driven(tmp_path: Path) -> None:
    """Absent an injected gatekeeper, the engine still runs (config-driven default)."""
    runs_dir = Path(str(tmp_path))
    cfg = config(rounds=1)
    engine = DebateEngine(cfg, models=_models(), runs_dir=runs_dir)
    result = engine.run(TOPIC, run_id="e6")
    assert isinstance(result, DebateResult)
    assert len([m for m in result.transcript if m.side is DebateSide.PRO]) == 1
