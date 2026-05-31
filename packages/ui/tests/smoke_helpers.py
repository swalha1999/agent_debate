"""Shared fixtures for the UI completed-debate smoke test (task 11.8, #80).

Keeps :mod:`test_ui_completed_debate_smoke` under the 150-line limit
(guideline §7.2): a rich, canned *completed* :class:`~agent_debate.core.
DebateResult` (Pro/Con transcript + a full verdict with winner/summary/
converged + token totals) and the canned ordered event sequence a streamed run
publishes, plus the two app builders the smoke test drives.

NO network, NO API key: the API app installs a stub *streaming* runner on
``app.state`` via the 10.3 seam (:func:`set_stream_runner`), so the whole
completed-debate HTTP surface the UI calls is exercised over a mocked engine.
The UI app is the real :func:`~agent_debate.ui.app.create_app` serving its
static shell. This is the honest "end-to-end without a browser" proof.
"""

from __future__ import annotations

import json

from agent_debate.api.app import create_app as create_api_app
from agent_debate.api.stream_runner import set_stream_runner
from agent_debate.core import (
    CostTotals,
    DebateMessage,
    DebateResult,
    DebateSide,
    Verdict,
)
from agent_debate.log import LogEvent
from fastapi import FastAPI

#: A representative completed-debate topic reused across the smoke flow.
TOPIC = "Should cities ban private cars from downtown?"

#: Ordered, typed events a streamed run publishes: Pro/Con messages, a moderator
#: nudge and the closing verdict — the exact sequence app.js routes to its
#: transcript / controller / verdict regions, ending before the ``done`` sentinel.
CANNED_EVENTS = [
    LogEvent(run_id="r", round=1, agent="pro", event_type="message", payload={"content": "for"}),
    LogEvent(run_id="r", round=1, agent="con", event_type="message", payload={"content": "no"}),
    LogEvent(run_id="r", round=2, agent="controller", event_type="nudge", payload={"reason": "x"}),
    LogEvent(run_id="r", round=2, agent="judge", event_type="verdict", payload={"winner": "pro"}),
]


def completed_result(topic: str) -> DebateResult:
    """Return a complete :class:`DebateResult` (transcript + verdict + totals).

    The verdict carries the exact fields the UI's verdict view reads — ``winner``,
    ``summary`` and ``converged`` — and the totals carry the token counts the view
    renders (``total_tokens`` / ``input_tokens`` / ``output_tokens``).
    """
    transcript = [
        DebateMessage(
            round=1, side=DebateSide.PRO, content="Cars choke downtowns.", output_tokens=11
        ),
        DebateMessage(round=1, side=DebateSide.CON, content="Bans hurt commerce.", output_tokens=9),
    ]
    return DebateResult(
        topic=topic,
        transcript=transcript,
        verdict=Verdict(
            winner=DebateSide.PRO,
            rationale="The pro side carried the burden of proof.",
            summary="A close debate; the pro side's evidence prevailed.",
            converged=True,
            scores={DebateSide.PRO: 0.7, DebateSide.CON: 0.3},
        ),
        totals=CostTotals.from_messages(transcript),
    )


def api_app() -> FastAPI:
    """Return the API app whose streaming runner returns the completed debate.

    Installs a stub via the 10.3 ``set_stream_runner`` seam: it publishes the
    canned events live (the SSE stream the UI reads) then returns the completed
    :class:`DebateResult` ``GET /debates/{id}`` surfaces — no network, no key.
    """
    app = create_api_app()

    def _runner(topic, overrides, publish, run_id):  # type: ignore[no-untyped-def]
        for event in CANNED_EVENTS:
            publish(event)
        return completed_result(topic)

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
    "api_app",
    "completed_result",
    "parse_sse",
]
