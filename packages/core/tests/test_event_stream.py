"""Tests for engine event STREAMING (issue #51, task 6.6, orchestration §6).

TDD-first: these assert the §6 streaming contract before the sink/generator
surface exists. The engine must YIELD ordered, typed events as they happen so
CLI (Epic 9) / API SSE (Epic 10) / UI (Epic 11) can render live — in addition
to (not instead of) logging them to ``runs/<run_id>.jsonl``.

The core assertions: streamed events are ORDERED and COMPLETE (equal, in order,
to the sequence written to the JSONL log), every ``event_type`` is within the
:data:`~agent_debate.log.EVENT_TYPES` literal, a consumer reads a ``message``
event live BEFORE the ``nudge`` that follows it, the generator re-raises a worker
error, and passing no sink is backward compatible. Shared offline fixtures
(FunctionModel agents, injected gatekeeper, JSONL helpers) live in
``_event_stream_helpers``.
"""

from __future__ import annotations

from pathlib import Path

from _event_stream_helpers import (
    TOPIC,
    BoomGatekeeper,
    config,
    key,
    logged_events,
    models,
    spy_gatekeeper,
    text_model,
)
from agent_debate.core import DebateResult, DebateSide, setup_debate
from agent_debate.core.engine import CollectingSink, run_debate_loop, stream_debate
from agent_debate.log import EVENT_TYPES, LogEvent


def _setup(pro: str = "pro point", con: str = "con rebut"):  # type: ignore[no-untyped-def]
    cfg = config(rounds=1)
    return setup_debate(TOPIC, cfg, models=models(pro=text_model(pro), con=text_model(con)))


def test_sink_receives_typed_events_in_order(tmp_path: Path) -> None:
    """A passed sink receives ordered, typed events covering the message sequence."""
    runs_dir = Path(str(tmp_path))
    sink = CollectingSink()
    setup = _setup()
    result = run_debate_loop(
        setup,
        config(),
        gatekeeper=spy_gatekeeper("s1", runs_dir),
        run_id="s1",
        runs_dir=runs_dir,
        sink=sink,
    )
    assert isinstance(result, DebateResult)
    assert sink.events, "expected the sink to receive events"
    assert all(isinstance(e, LogEvent) for e in sink.events)
    assert all(e.event_type in EVENT_TYPES for e in sink.events)
    messages = [
        e for e in sink.events if e.event_type == "message" and not e.payload.get("closing")
    ]
    assert [(m.round, m.agent) for m in messages[:2]] == [(1, "pro"), (1, "con")]


def test_streamed_events_match_jsonl_log_exactly(tmp_path: Path) -> None:
    """Streamed events are ordered + complete: identical sequence to the JSONL log."""
    runs_dir = Path(str(tmp_path))
    sink = CollectingSink()
    setup = setup_debate(
        TOPIC,
        config(rounds=2),
        models=models(pro=text_model("pro point"), con=text_model("con")),
    )
    run_debate_loop(
        setup,
        config(rounds=2),
        gatekeeper=spy_gatekeeper("s2", runs_dir),
        run_id="s2",
        runs_dir=runs_dir,
        sink=sink,
    )
    streamed = [key(e) for e in sink.events]
    logged = [key(e) for e in logged_events(runs_dir, "s2")]
    assert streamed == logged, "streamed events must equal the JSONL sequence, in order"


def test_message_streams_before_following_nudge(tmp_path: Path) -> None:
    """A consumer reads the Pro ``message`` event live BEFORE the ``nudge`` that follows."""
    runs_dir = Path(str(tmp_path))
    sink = CollectingSink()
    setup = _setup(pro="You're right, I concede.")
    run_debate_loop(
        setup,
        config(),
        gatekeeper=spy_gatekeeper("s3", runs_dir),
        run_id="s3",
        runs_dir=runs_dir,
        sink=sink,
    )
    types = [e.event_type for e in sink.events]
    assert "nudge" in types, "expected a nudge for the captured Pro"
    first_message = next(i for i, e in enumerate(sink.events) if e.event_type == "message")
    first_nudge = next(i for i, e in enumerate(sink.events) if e.event_type == "nudge")
    assert first_message < first_nudge


def test_generator_yields_events_live(tmp_path: Path) -> None:
    """``stream_debate`` yields typed events; the final item carries the result."""
    runs_dir = Path(str(tmp_path))
    setup = _setup()
    events: list[LogEvent] = []
    result: DebateResult | None = None
    for item in stream_debate(
        setup, config(), gatekeeper=spy_gatekeeper("s4", runs_dir), run_id="s4", runs_dir=runs_dir
    ):
        if isinstance(item, LogEvent):
            events.append(item)
        else:
            result = item
    assert events, "generator should yield events"
    assert all(e.event_type in EVENT_TYPES for e in events)
    assert isinstance(result, DebateResult)
    assert [key(e) for e in events] == [key(e) for e in logged_events(runs_dir, "s4")]


def test_generator_propagates_worker_error(tmp_path: Path) -> None:
    """An error in the threaded debate surfaces out of the generator to the caller."""
    runs_dir = Path(str(tmp_path))
    setup = _setup()
    gen = stream_debate(
        setup, config(), gatekeeper=BoomGatekeeper(), run_id="s6", runs_dir=runs_dir
    )
    raised = False
    try:
        for _ in gen:
            pass
    except ValueError as exc:
        raised = "boom" in str(exc)
    assert raised, "the worker's error must propagate to the generator consumer"


def test_no_sink_is_backward_compatible(tmp_path: Path) -> None:
    """Omitting the sink leaves the loop's existing return contract unchanged."""
    runs_dir = Path(str(tmp_path))
    setup = _setup()
    result = run_debate_loop(
        setup, config(), gatekeeper=spy_gatekeeper("s5", runs_dir), run_id="s5", runs_dir=runs_dir
    )
    assert isinstance(result, DebateResult)
    assert len([m for m in result.transcript if m.side is DebateSide.PRO]) == 1
