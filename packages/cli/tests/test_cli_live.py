"""Tests for the Rich LIVE transcript renderer (task 9.2, issue #65).

The ``run`` command consumes :meth:`DebateEngine.stream` and renders each ordered
:class:`~agent_debate.log.LogEvent` LIVE via Rich (Pro/Con messages per round,
inline controller nudges, the final verdict). These tests drive the renderer with
a stub engine yielding a CANNED event sequence — Pro message, Con message, a
nudge, then the verdict — so the path is exercised with NO network / API key.

We assert the rendered output contains the Pro/Con messages (distinguished), the
nudge inline (between the turns it sits among), and the verdict at the end — in
that order; and that the renderer streams (prints per event, not only at the end).
"""

from __future__ import annotations

from collections.abc import Iterator

import agent_debate.cli.app as cli_app
import pytest
from agent_debate.core import DebateConfig, Settings
from agent_debate.core.engine.result import DebateResult
from agent_debate.core.skills.models import DebateSide, Verdict
from agent_debate.log import LogEvent
from typer.testing import CliRunner

runner = CliRunner()

_RUN_ID = "test-run"


def _message_event(side: DebateSide, content: str, round_: int) -> LogEvent:
    return LogEvent(
        run_id=_RUN_ID,
        round=round_,
        agent=side.value,
        event_type="message",
        payload={"content": content, "word_count": len(content.split())},
    )


def _nudge_event(round_: int) -> LogEvent:
    return LogEvent(
        run_id=_RUN_ID,
        round=round_,
        agent="controller",
        event_type="nudge",
        payload={
            "target": DebateSide.PRO.value,
            "reason": "drifting off topic",
            "correction": "return to the resolution",
            "confidence": 0.9,
        },
    )


def _verdict_event() -> LogEvent:
    return LogEvent(
        run_id=_RUN_ID,
        round=0,
        agent="controller",
        event_type="verdict",
        payload={
            "winner": DebateSide.PRO.value,
            "converged": False,
            "summary": "pro prevailed",
            "rationale": "tighter reasoning",
        },
    )


def _canned_events() -> list[LogEvent | DebateResult]:
    """Pro message, Con message, a nudge, the verdict, then the final result."""
    return [
        _message_event(DebateSide.PRO, "pro opening statement", 1),
        _message_event(DebateSide.CON, "con rebuttal point", 1),
        _nudge_event(1),
        _verdict_event(),
        DebateResult(
            topic="a topic",
            verdict=Verdict(
                winner=DebateSide.PRO,
                rationale="tighter reasoning",
                scores={DebateSide.PRO: 2.0, DebateSide.CON: 1.0},
                summary="pro prevailed",
            ),
        ),
    ]


class _StreamingEngine:
    """Stub engine that streams a canned event sequence (no network)."""

    last_topic: str | None = None

    def __init__(self, config: DebateConfig | None = None, **kwargs: object) -> None:
        pass

    def stream(self, topic: str) -> Iterator[LogEvent | DebateResult]:
        type(self).last_topic = topic
        yield from _canned_events()


@pytest.fixture(autouse=True)
def _patch_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Swap in the streaming stub + a frozen ``Settings`` (no network/key)."""
    _StreamingEngine.last_topic = None
    monkeypatch.setattr(cli_app, "DebateEngine", _StreamingEngine)
    monkeypatch.setattr(cli_app, "get_settings", lambda: Settings(rounds=1, max_words=40))


def test_run_streams_and_consumes_engine_stream() -> None:
    """``run`` drives ``DebateEngine.stream`` (not ``run``) on the topic."""
    result = runner.invoke(cli_app.app, ["run", "a topic"])
    assert result.exit_code == 0, result.output
    assert _StreamingEngine.last_topic == "a topic"


def test_renders_pro_con_messages_distinguished() -> None:
    """Both debater messages render, labelled Pro vs Con distinctly."""
    result = runner.invoke(cli_app.app, ["run", "a topic"])
    assert result.exit_code == 0, result.output
    out = result.output
    assert "pro opening statement" in out
    assert "con rebuttal point" in out
    assert "Pro" in out
    assert "Con" in out


def test_renders_nudge_inline_between_turns() -> None:
    """The controller nudge renders inline, after the turns it sits among."""
    result = runner.invoke(cli_app.app, ["run", "a topic"])
    out = result.output
    assert "return to the resolution" in out
    assert "nudge" in out.lower()
    # Inline: the nudge appears after both debater turns it followed.
    assert out.index("con rebuttal point") < out.index("return to the resolution")


def test_render_stream_skips_unsurfaced_events_and_minimal_verdict() -> None:
    """Unhandled kinds (e.g. tool_call) are ignored; a bare verdict still renders."""
    from agent_debate.cli._live import render_stream
    from rich.console import Console

    events: list[LogEvent | DebateResult] = [
        LogEvent(run_id=_RUN_ID, round=1, agent="pro", event_type="tool_call", payload={}),
        LogEvent(
            run_id=_RUN_ID,
            round=0,
            agent="controller",
            event_type="verdict",
            payload={"winner": DebateSide.PRO.value},
        ),
    ]
    console = Console(record=True, width=80)
    result = render_stream("a topic", iter(events), console=console)
    text = console.export_text()
    assert result is None
    assert "Verdict" in text
    assert "Summary" not in text and "Rationale" not in text


def test_renders_verdict_last_in_order() -> None:
    """Messages, then nudge, then verdict — verdict rendered at the end."""
    result = runner.invoke(cli_app.app, ["run", "a topic"])
    out = result.output
    assert "pro prevailed" in out or "tighter reasoning" in out
    assert "Verdict" in out
    nudge_at = out.index("return to the resolution")
    verdict_at = out.index("Verdict")
    assert nudge_at < verdict_at
