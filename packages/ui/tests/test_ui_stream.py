"""Tests for the live streaming transcript wiring (task 11.2, issue #74).

The live transcript is browser JS consuming the API's SSE endpoint
``GET /debates/{id}/stream`` and rendering the Pro vs Con messages as they
arrive. A real browser cannot run under pytest, so (as for 11.1) these tests
assert at the *serving* level: the served page + ``app.js`` are wired up to
open an ``EventSource`` against the config-driven ``{API_BASE_URL}/debates/
{id}/stream`` path, dispatch ``message`` events and render distinct Pro/Con
sides, closing on the ``done`` sentinel. Browser behaviour itself is exercised
by the UI smoke test (task 11.8); the honest contract here is the wiring.
"""

from __future__ import annotations

from agent_debate.ui.app import create_app
from fastapi.testclient import TestClient


def _app_js() -> str:
    """Return the served ``app.js`` source (lower-cased for substring checks)."""
    client = TestClient(create_app())
    response = client.get("/static/app.js")
    assert response.status_code == 200
    return response.text


def test_app_js_uses_eventsource_for_sse() -> None:
    """The frontend consumes SSE via the browser ``EventSource`` API."""
    assert "EventSource" in _app_js()


def test_app_js_targets_the_stream_path() -> None:
    """``app.js`` opens the stream against ``/debates/<id>/stream``."""
    source = _app_js()
    assert "/debates/" in source
    assert "/stream" in source


def test_stream_url_uses_config_driven_api_base_url() -> None:
    """The stream URL is built from the injected, config-driven API base URL."""
    source = _app_js()
    # The same ``apiBaseUrl()`` helper that 11.1 uses for POST /debates must
    # also build the stream URL — never a hard-coded origin.
    assert "apiBaseUrl()" in source
    assert "${apiBaseUrl()}/debates/" in source


def test_app_js_dispatches_message_events_and_done_sentinel() -> None:
    """The consumer listens for ``message`` events and stops on ``done``."""
    source = _app_js()
    assert 'addEventListener("message"' in source
    assert 'addEventListener("done"' in source
    assert ".close()" in source


def test_app_js_renders_pro_and_con_sides() -> None:
    """Rendering distinguishes Pro from Con (per the DebateSide values)."""
    source = _app_js().lower()
    assert "pro" in source
    assert "con" in source
    assert "round" in source


def test_index_has_transcript_container() -> None:
    """The page exposes a transcript region for the live render to fill."""
    client = TestClient(create_app())
    body = client.get("/").text.lower()
    assert 'id="transcript"' in body


def test_style_distinguishes_pro_and_con() -> None:
    """The stylesheet gives Pro and Con visually distinct treatments."""
    client = TestClient(create_app())
    css = client.get("/static/style.css").text.lower()
    assert ".turn--pro" in css
    assert ".turn--con" in css


def test_style_is_rtl_safe_logical_properties_only() -> None:
    """Transcript CSS uses logical properties only (no physical left/right)."""
    client = TestClient(create_app())
    css = client.get("/static/style.css").text
    banned = (
        "margin-left",
        "margin-right",
        "padding-left",
        "padding-right",
        "text-align: left",
        "text-align: right",
    )
    for token in banned:
        assert token not in css
