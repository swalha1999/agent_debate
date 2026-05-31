"""Unit tests for the SSE streaming internals (task 10.3, issue #70).

Covers the per-run :class:`~agent_debate.api.event_buffer.EventBuffer` live-wait
path, the backward-compatible adaptation of a non-streaming
:class:`~agent_debate.api.debate_runner.DebateRunner`, and
:func:`~agent_debate.api.stream_runner.default_stream_runner` driving
:meth:`DebateEngine.stream` (the engine stubbed, so no network/API key).
"""

from __future__ import annotations

import threading
import time

import agent_debate.api.stream_runner as stream_mod
import pytest
from agent_debate.api.app import create_app
from agent_debate.api.debate_runner import set_debate_runner
from agent_debate.api.event_buffer import EventBuffer
from agent_debate.api.stream_runner import (
    default_stream_runner,
    get_stream_runner,
)
from agent_debate.core import DebateResult
from agent_debate.log import LogEvent

_TOPIC = "Should cities ban cars from downtown?"


def _event() -> LogEvent:
    return LogEvent(run_id="r", round=1, agent="pro", event_type="message")


def test_buffer_blocks_for_a_live_event_then_closes() -> None:
    """A consumer waiting before any event sees it once published, then close."""
    buffer = EventBuffer()

    def _produce() -> None:
        time.sleep(0.05)
        buffer.publish(_event())
        buffer.close()

    threading.Thread(target=_produce).start()
    collected = list(buffer.stream())  # blocks on the empty buffer first

    assert [e.event_type for e in collected] == ["message"]


def test_get_stream_runner_adapts_a_plain_runner() -> None:
    """A non-streaming runner installed via 10.2 is adapted (backward compat)."""
    app = create_app()
    set_debate_runner(app, lambda topic, overrides: DebateResult(topic=topic))

    runner = get_stream_runner(app)
    result = runner(_TOPIC, {}, lambda event: None, "rid")

    assert result.topic == _TOPIC


def test_get_stream_runner_defaults_when_unset() -> None:
    """With nothing installed, the default streaming runner is returned."""
    app = create_app()

    assert get_stream_runner(app) is default_stream_runner


def test_default_stream_runner_publishes_then_returns_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``default_stream_runner`` forwards stream events and returns the result."""

    class _FakeEngine:
        def __init__(self, config: object, *, settings: object) -> None: ...

        def stream(self, topic: str, *, run_id: str):  # type: ignore[no-untyped-def]
            yield _event()
            yield DebateResult(topic=topic)

    monkeypatch.setattr(stream_mod, "DebateEngine", _FakeEngine)
    published: list[LogEvent] = []

    def _publish(event: LogEvent) -> None:
        published.append(event)

    result = default_stream_runner(_TOPIC, {"rounds": 2}, _publish, "rid")

    assert result.topic == _TOPIC
    assert [e.event_type for e in published] == ["message"]
