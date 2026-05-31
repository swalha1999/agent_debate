"""Epic-10 acceptance: the API is a correct HTTP surface over the SDK (#72).

Consolidates the headline API flows end-to-end with ``TestClient`` and a MOCKED
engine (no network, no API key — runners are stubbed via ``app.state``):

* lifecycle: ``POST /debates`` -> ``run_id`` -> ``GET /debates/{id}`` polls to
  ``done`` carrying the full :class:`~agent_debate.core.DebateResult` (transcript
  + verdict);
* the stream endpoint emits the run's ordered, typed SSE events;
* errors are consistent (unknown id -> 404 envelope, invalid topic -> 422
  envelope) and CORS allows the configured UI origin.

Per-task suites (10.2/10.3/10.4) cover each route in isolation; the net-new value
here is the *integrated* start -> poll -> rich-result and the stream composition
of the same surface as one acceptance story.
"""

from __future__ import annotations

from acceptance_helpers import TOPIC, parse_sse, result_app, stream_app
from agent_debate.api.config import DEFAULT_UI_ORIGIN
from agent_debate.api.debate_runner import default_runner, get_debate_runner
from agent_debate.api.debate_store import DebateStatus
from agent_debate.api.errors import ERROR_KEY
from agent_debate.api.sse import DONE_EVENT
from fastapi.testclient import TestClient


def test_lifecycle_start_poll_returns_status_and_full_result() -> None:
    """POST starts a run; GET polls it to ``done`` with transcript + verdict."""
    client = TestClient(result_app())

    started = client.post("/debates", json={"topic": TOPIC})
    assert started.status_code == 201
    run_id = started.json()["run_id"]
    assert run_id and started.json()["status"] in {DebateStatus.RUNNING, DebateStatus.DONE}

    state = client.get(f"/debates/{run_id}")
    assert state.status_code == 200
    body = state.json()
    assert body["run_id"] == run_id
    assert body["status"] == DebateStatus.DONE
    result = body["result"]
    assert result["topic"] == TOPIC
    assert [m["side"] for m in result["transcript"]] == ["pro", "con"]
    assert result["verdict"]["winner"] == "pro"
    assert body["error"] is None


def test_stream_endpoint_emits_ordered_typed_events_for_a_run() -> None:
    """The stream emits the run's ordered events, ending with the done sentinel."""
    client = TestClient(stream_app())
    run_id = client.post("/debates", json={"topic": TOPIC}).json()["run_id"]

    response = client.get(f"/debates/{run_id}/stream")

    assert response.status_code == 200
    parsed = parse_sse(response.text)
    assert [name for name, _ in parsed] == ["message", "message", "nudge", "verdict", DONE_EVENT]
    assert parsed[-1][1]["status"] == DebateStatus.DONE
    assert parsed[-1][1]["run_id"] == run_id


def test_streamed_run_is_also_pollable_to_a_done_result() -> None:
    """A streamed run lands in the store and GET reports ``done`` with a result."""
    client = TestClient(stream_app())
    run_id = client.post("/debates", json={"topic": TOPIC}).json()["run_id"]

    body = client.get(f"/debates/{run_id}").json()

    assert body["status"] == DebateStatus.DONE
    assert body["result"]["verdict"]["winner"] == "pro"


def test_unknown_run_id_is_a_consistent_404_envelope() -> None:
    """An unknown run_id returns the shared ``{"error": ...}`` envelope (404)."""
    client = TestClient(result_app())

    response = client.get("/debates/missing")

    assert response.status_code == 404
    assert set(response.json()[ERROR_KEY]) == {"type", "message", "detail"}


def test_invalid_topic_is_a_consistent_422_envelope() -> None:
    """An oversized topic is a 422 in the shared error envelope (no run started)."""
    client = TestClient(result_app())

    response = client.post("/debates", json={"topic": "x" * 5000})

    assert response.status_code == 422
    assert response.json()[ERROR_KEY]["type"] == "validation_error"


def test_cors_allows_the_configured_ui_origin() -> None:
    """A browser request from the configured UI origin is allowed by CORS."""
    client = TestClient(result_app())

    response = client.get("/health", headers={"Origin": DEFAULT_UI_ORIGIN})

    assert response.headers.get("access-control-allow-origin") == DEFAULT_UI_ORIGIN


def test_get_debate_runner_defaults_to_the_sdk_runner() -> None:
    """With no injected runner the accessor resolves to the production SDK seam."""
    app = result_app()
    delattr(app.state, "debate_runner")

    assert get_debate_runner(app) is default_runner
