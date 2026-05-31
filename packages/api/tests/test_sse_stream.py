"""Tests for the SSE stream endpoint (task 10.3, issue #70).

TDD: assert the ``GET /debates/{id}/stream`` contract before the code exists.
Tests run with NO network and NO API key — a stub streaming runner publishes a
canned sequence of :class:`~agent_debate.log.LogEvent` into the per-run event
buffer, and the SSE endpoint drains them. ``TestClient`` buffers a
``StreamingResponse`` fully, so we parse the complete SSE body and assert the
events appear in order with the correct event names (``event_type``) and JSON
``data`` payloads, that an unknown id is a 404, and that the stream terminates.
"""

from __future__ import annotations

import json

from agent_debate.api.app import create_app
from agent_debate.api.sse import DONE_EVENT, SSE_MEDIA_TYPE
from agent_debate.api.stream_runner import set_stream_runner
from agent_debate.core import DebateResult
from agent_debate.log import LogEvent
from fastapi import FastAPI
from fastapi.testclient import TestClient

_TOPIC = "Should cities ban cars from downtown?"

_CANNED_EVENTS = [
    LogEvent(run_id="r", round=1, agent="pro", event_type="message", payload={"text": "hi"}),
    LogEvent(run_id="r", round=1, agent="controller", event_type="nudge", payload={"why": "drift"}),
    LogEvent(run_id="r", round=2, agent="judge", event_type="verdict", payload={"winner": "pro"}),
]


def _stub_streaming_app() -> FastAPI:
    """Build an app whose streaming runner publishes canned events, no network."""
    app = create_app()

    def _runner(topic: str, overrides: dict[str, object], publish, run_id: str):  # type: ignore[no-untyped-def]
        for event in _CANNED_EVENTS:
            publish(event)
        return DebateResult(topic=topic)

    set_stream_runner(app, _runner)
    return app


def _start(client: TestClient) -> str:
    """Start a debate and return its run_id."""
    run_id: str = client.post("/debates", json={"topic": _TOPIC}).json()["run_id"]
    return run_id


def _parse_sse(body: str) -> list[tuple[str, dict[str, object]]]:
    """Parse an SSE body into ``[(event_name, json_data), ...]`` in order."""
    parsed: list[tuple[str, dict[str, object]]] = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        name = ""
        data = ""
        for line in block.splitlines():
            if line.startswith("event:"):
                name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data += line[len("data:") :].strip()
        parsed.append((name, json.loads(data)))
    return parsed


def test_stream_yields_ordered_typed_events() -> None:
    """The stream returns text/event-stream with events in order, typed."""
    client = TestClient(_stub_streaming_app())
    run_id = _start(client)

    response = client.get(f"/debates/{run_id}/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(SSE_MEDIA_TYPE)
    parsed = _parse_sse(response.text)
    names = [name for name, _ in parsed]
    assert names == ["message", "nudge", "verdict", DONE_EVENT]
    assert parsed[0][1]["payload"] == {"text": "hi"}
    assert parsed[2][1]["event_type"] == "verdict"


def test_stream_terminates_with_done_sentinel() -> None:
    """The final SSE event is the ``done`` sentinel and the stream closes."""
    client = TestClient(_stub_streaming_app())
    run_id = _start(client)

    parsed = _parse_sse(client.get(f"/debates/{run_id}/stream").text)

    assert parsed[-1][0] == DONE_EVENT


def test_stream_unknown_run_id_returns_404() -> None:
    """An unknown run_id streams nothing and returns 404."""
    client = TestClient(_stub_streaming_app())

    response = client.get("/debates/does-not-exist/stream")

    assert response.status_code == 404


def test_finished_debate_replays_its_events() -> None:
    """A run completed before the stream opens replays its buffered events."""
    client = TestClient(_stub_streaming_app())
    run_id = _start(client)
    # First read drains/replays; a second read must still replay (buffer kept).
    client.get(f"/debates/{run_id}/stream")

    parsed = _parse_sse(client.get(f"/debates/{run_id}/stream").text)

    names = [name for name, _ in parsed]
    assert names == ["message", "nudge", "verdict", DONE_EVENT]
