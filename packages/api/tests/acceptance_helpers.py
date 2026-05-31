"""Shared fixtures for the Epic-10 API acceptance suite (task 10.5, issue #72).

Keeps :mod:`test_api_acceptance` under the 150-line limit (guideline §7.2): a
rich, canned :class:`~agent_debate.core.DebateResult` (transcript + verdict) and
the canned ordered :class:`~agent_debate.log.LogEvent` sequence, plus the two
app builders (a non-streaming runner and a streaming runner) and an SSE parser.

NO network, NO API key: both runners are stubs installed on ``app.state`` via the
10.2/10.3 seams (:func:`set_debate_runner` / :func:`set_stream_runner`), so the
HTTP surface is exercised end-to-end over a mocked engine.
"""

from __future__ import annotations

import json

from agent_debate.api.app import create_app
from agent_debate.api.debate_runner import set_debate_runner
from agent_debate.api.stream_runner import set_stream_runner
from agent_debate.core import DebateMessage, DebateResult, DebateSide, Verdict
from agent_debate.log import LogEvent
from fastapi import FastAPI

#: A representative debate topic reused across the acceptance flows.
TOPIC = "Should cities ban cars from downtown?"

#: Ordered, typed events a streamed run publishes (message -> nudge -> verdict).
CANNED_EVENTS = [
    LogEvent(run_id="r", round=1, agent="pro", event_type="message", payload={"text": "for"}),
    LogEvent(run_id="r", round=1, agent="con", event_type="message", payload={"text": "against"}),
    LogEvent(run_id="r", round=2, agent="controller", event_type="nudge", payload={"why": "drift"}),
    LogEvent(run_id="r", round=2, agent="judge", event_type="verdict", payload={"winner": "pro"}),
]


def rich_result(topic: str) -> DebateResult:
    """Return a complete :class:`DebateResult` with a transcript and a verdict."""
    return DebateResult(
        topic=topic,
        transcript=[
            DebateMessage(round=1, side=DebateSide.PRO, content="Cars choke downtowns."),
            DebateMessage(round=1, side=DebateSide.CON, content="Bans hurt commerce."),
        ],
        verdict=Verdict(
            winner=DebateSide.PRO,
            rationale="The pro side carried the burden of proof.",
            scores={DebateSide.PRO: 0.7, DebateSide.CON: 0.3},
        ),
    )


def result_app() -> FastAPI:
    """App whose (non-streaming) runner returns the rich canned result."""
    app = create_app()
    set_debate_runner(app, lambda topic, overrides: rich_result(topic))
    return app


def stream_app() -> FastAPI:
    """App whose streaming runner publishes the canned events then the result."""
    app = create_app()

    def _runner(topic, overrides, publish, run_id):  # type: ignore[no-untyped-def]
        for event in CANNED_EVENTS:
            publish(event)
        return rich_result(topic)

    set_stream_runner(app, _runner)
    return app


def parse_sse(body: str) -> list[tuple[str, dict[str, object]]]:
    """Parse an SSE body into ordered ``[(event_name, json_data), ...]`` pairs."""
    parsed: list[tuple[str, dict[str, object]]] = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        name, data = "", ""
        for line in block.splitlines():
            if line.startswith("event:"):
                name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data += line[len("data:") :].strip()
        parsed.append((name, json.loads(data)))
    return parsed


__all__ = [
    "CANNED_EVENTS",
    "TOPIC",
    "parse_sse",
    "result_app",
    "rich_result",
    "stream_app",
]
