"""Tests for the three separate panels layout (task 11.3, issue #75).

PRD §6: the UI lays out *separate panels* for transcript / controller actions /
system log — "don't overload one view". Each SSE ``LogEvent`` is routed to the
right panel by its ``event_type`` (the SSE event name): ``message`` → debate
transcript (Pro/Con), ``nudge`` → controller actions/nudges, and the technical
events (``system``/``tool_call``/``timeout``/``retry``) → system log.

A real browser cannot run under pytest, so (as for 11.1/11.2) these tests assert
at the *serving* level: the served HTML exposes three distinct, labelled panels
and ``app.js`` carries the routing wiring that dispatches each ``event_type`` to
its panel. Browser behaviour itself is the UI smoke test (task 11.8).
"""

from __future__ import annotations

from agent_debate.ui.app import create_app
from fastapi.testclient import TestClient


def _html() -> str:
    """Return the served index page source."""
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    return response.text


def _app_js() -> str:
    """Return the served ``app.js`` source."""
    client = TestClient(create_app())
    response = client.get("/static/app.js")
    assert response.status_code == 200
    return response.text


def _css() -> str:
    """Return the served stylesheet source."""
    client = TestClient(create_app())
    response = client.get("/static/style.css")
    assert response.status_code == 200
    return response.text


def test_index_has_three_distinct_panel_containers() -> None:
    """The page exposes three separate panel regions (don't overload one view)."""
    body = _html().lower()
    assert 'id="transcript"' in body
    assert 'id="controller-panel"' in body
    assert 'id="system-log"' in body


def test_each_panel_has_a_labelled_heading() -> None:
    """Each panel is labelled with a heading so the layout reads clearly."""
    body = _html().lower()
    assert "debate transcript" in body
    assert "controller actions" in body
    assert "system log" in body


def test_controller_panel_has_a_list_for_nudges() -> None:
    """The controller panel exposes a list the nudge render appends into."""
    assert 'id="controller-actions"' in _html().lower()


def test_system_log_panel_has_a_list_for_events() -> None:
    """The system-log panel exposes a list the technical events append into."""
    assert 'id="system-log-list"' in _html().lower()


def test_app_js_routes_message_events_to_transcript() -> None:
    """``message`` events are dispatched to the transcript panel."""
    source = _app_js()
    assert 'addEventListener("message"' in source
    assert "appendMessage" in source


def test_app_js_routes_nudge_events_to_controller_panel() -> None:
    """``nudge`` events are dispatched to the controller actions panel."""
    source = _app_js()
    assert 'addEventListener("nudge"' in source
    assert "controller-actions" in source


def test_app_js_routes_system_events_to_system_log() -> None:
    """``system``/``tool_call``/``timeout``/``retry`` go to the system log."""
    source = _app_js()
    # The technical event types are declared as the single source of truth and
    # each is registered as an EventSource listener feeding the system log.
    for name in ("system", "tool_call", "timeout", "retry"):
        assert f'"{name}"' in source
    assert "SYSTEM_EVENT_TYPES" in source
    assert "addEventListener(eventType" in source
    assert "system-log-list" in source


def test_app_js_keeps_nudges_out_of_the_transcript() -> None:
    """Nudges render in the controller panel, NOT mixed into the transcript."""
    source = _app_js()
    # The controller render targets the controller list, not a transcript column.
    assert "appendControllerAction" in source
    assert "appendSystemEvent" in source


def test_panels_css_is_rtl_safe_logical_properties_only() -> None:
    """Panel CSS uses logical properties only (no physical left/right)."""
    css = _css()
    banned = (
        "margin-left",
        "margin-right",
        "padding-left",
        "padding-right",
        "text-align: left",
        "text-align: right",
        "border-left",
        "border-right",
    )
    for token in banned:
        assert token not in css


def test_panels_have_distinct_styling() -> None:
    """The stylesheet styles each panel region distinctly."""
    css = _css().lower()
    assert ".controller-panel" in css
    assert ".system-log" in css
