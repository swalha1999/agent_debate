"""UI smoke test for a *completed* debate (task 11.8, issue #80).

The required deliverable for #80: an honest end-to-end smoke proof that the UI
works for a finished debate WITHOUT a real browser. A real Playwright/Selenium
render is neither available nor appropriate in headless CI, so this drives the
flow at the serving / integration level in three parts:

1. UI SHELL — :func:`~agent_debate.ui.app.create_app` serves ``GET /`` as the
   full page a user sees: the topic input, the three panels, the verdict region
   and the status indicator (the complete shell).
2. API COMPLETED-DEBATE CONTRACT — the API app, driven by a stub streaming
   runner that returns a canned completed :class:`~agent_debate.core.
   DebateResult`, satisfies the exact surface the UI calls: ``POST /debates`` ->
   ``run_id``; ``GET /debates/{id}`` -> done + verdict + token totals;
   ``GET /debates/{id}/stream`` -> ordered SSE ending with the ``done`` sentinel.
3. UI↔API CROSS-CHECK — the served ``app.js`` references those exact paths and
   verdict fields (``winner`` / ``converged`` / ``summary`` + token totals), and
   those fields exist in the API's completed-debate response — so the client and
   the server line up.

No network, no API key: the stub runner is installed via the 10.3 seam.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from agent_debate.ui.app import create_app as create_ui_app
from fastapi.testclient import TestClient
from smoke_helpers import TOPIC, api_app, completed_result, parse_sse

#: Static frontend dir whose ``app.js`` the UI app serves (the real client code).
_STATIC = Path(__file__).resolve().parents[1] / "src" / "agent_debate" / "ui" / "static"

#: Element ids the full page shell a user sees must carry (input + every panel +
#: verdict region + status indicator). Single source of truth, no scattered ids.
_SHELL_IDS = (
    "topic",
    "start",
    "status",
    "transcript-pro",
    "transcript-con",
    "controller-actions",
    "system-log-list",
    "verdict",
)


@pytest.fixture
def ui_client() -> TestClient:
    """A ``TestClient`` over a fresh UI app serving the static shell."""
    return TestClient(create_ui_app())


@pytest.fixture
def api_client() -> TestClient:
    """A ``TestClient`` over the API app with the completed-debate stub runner."""
    return TestClient(api_app())


def test_ui_shell_serves_full_completed_debate_page(ui_client: TestClient) -> None:
    """``GET /`` returns the complete shell: input, three panels, verdict, status."""
    response = ui_client.get("/")
    assert response.status_code == 200
    body = response.text
    for element_id in _SHELL_IDS:
        assert f'id="{element_id}"' in body, element_id
    # The verdict region the completed debate fills + the status indicator copy.
    assert 'id="verdict"' in body and "Verdict" in body
    assert 'role="status"' in body


def test_api_completed_debate_status_contract(api_client: TestClient) -> None:
    """POST /debates -> run_id; GET /debates/{id} -> done + verdict + totals."""
    started = api_client.post("/debates", json={"topic": TOPIC})
    assert started.status_code == 201
    run_id = started.json()["run_id"]
    assert run_id

    state = api_client.get(f"/debates/{run_id}")
    assert state.status_code == 200
    payload = state.json()
    assert payload["status"] == "done"
    result = payload["result"]
    assert result["verdict"]["winner"] == "pro"
    assert result["verdict"]["summary"]
    assert result["verdict"]["converged"] is True
    assert result["totals"]["total_tokens"] == 20


def test_api_completed_debate_stream_ends_with_done(api_client: TestClient) -> None:
    """GET /debates/{id}/stream -> ordered SSE events ending with the verdict + done."""
    run_id = api_client.post("/debates", json={"topic": TOPIC}).json()["run_id"]
    api_client.get(f"/debates/{run_id}")  # let the run finish so the buffer closes.

    body = api_client.get(f"/debates/{run_id}/stream").text
    events = parse_sse(body)
    names = [name for name, _ in events]
    assert names == ["message", "message", "nudge", "verdict", "done"]
    assert events[-1][1]["status"] == "done"


def test_ui_client_and_api_response_fields_line_up(api_client: TestClient) -> None:
    """The served app.js calls the exact paths/fields the API completed run exposes."""
    app_js = (_STATIC / "app.js").read_text(encoding="utf-8")
    # The client builds these exact paths against the API.
    assert "/debates" in app_js
    assert "/debates/${encodeURIComponent(runId)}" in app_js
    assert "/debates/${encodeURIComponent(runId)}/stream" in app_js

    # The verdict fields app.js reads must exist in the API's completed response.
    for field in ("verdict.winner", "verdict.converged", "verdict.summary"):
        assert field.split(".")[-1] in app_js, field
    for total in ("total_tokens", "input_tokens", "output_tokens"):
        assert total in app_js, total

    dumped = completed_result(TOPIC).model_dump()
    assert {"winner", "converged", "summary"} <= dumped["verdict"].keys()
    assert {"total_tokens", "input_tokens", "output_tokens"} <= dumped["totals"].keys()
