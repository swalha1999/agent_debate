"""Nielsen usability heuristics for the UI (task 11.6, issue #78).

Guideline §10.1 / PRD §10: the interface is assessed against Nielsen's 10
usability heuristics. A real browser cannot run under pytest, so (as for
11.1–11.5) these tests assert at the *serving* level — they prove the served
HTML/JS carry the concrete, testable usability affordances:

* **Visibility of system status** — a status/round/streaming indicator element
  that ``app.js`` updates from SSE events (connecting → debating round N →
  complete → error).
* **Error prevention** — the Start button is disabled while a debate runs and
  for an empty topic (client-side validation before the POST).
* **Help users recover from errors** — a friendly, human error message on
  network/non-2xx/SSE failure (not a raw stack), with a retry hint.
* **User control & freedom** — a "new debate" / reset control so the user is
  never trapped.
* **Help & documentation** — a short help/about hint explaining the app.
* **Consistency & recognition over recall** — consistent Pro/Con/Moderator/
  Verdict terminology and visible labels.

Browser behaviour itself is the UI smoke test (task 11.8).
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


# --- Visibility of system status -----------------------------------------


def test_index_has_a_status_indicator_element() -> None:
    """A visible status region surfaces system status (connecting/round/done)."""
    body = _html().lower()
    assert 'id="status"' in body
    assert 'class="status' in body


def test_app_js_updates_status_from_sse_lifecycle() -> None:
    """``app.js`` updates the status across the debate lifecycle."""
    source = _app_js()
    assert "setStatus" in source
    # Lifecycle states: connecting, live/debating (with round), complete, error.
    assert "Connecting" in source
    assert "Complete" in source
    assert "round" in source.lower()


def test_app_js_shows_a_live_streaming_indicator() -> None:
    """A streaming/"live" indicator is toggled while events arrive."""
    source = _app_js()
    assert "live" in source.lower()


# --- Error prevention -----------------------------------------------------


def test_app_js_disables_start_while_running_and_for_empty_topic() -> None:
    """The Start button is disabled while running / when the topic is empty."""
    source = _app_js()
    assert "button.disabled = true" in source
    # Empty-topic validation guards the POST.
    assert "input.value.trim()" in source
    assert "Please enter a topic" in source


def test_app_js_validates_topic_before_post() -> None:
    """Validation returns early (no POST) on an empty topic."""
    source = _app_js()
    # The empty-topic branch returns before the POST is awaited.
    idx_guard = source.find("Please enter a topic")
    idx_post = source.find("await startDebate(topic)")
    assert idx_guard != -1 and idx_post != -1
    assert idx_guard < idx_post


# --- Help users recover from errors --------------------------------------


def test_app_js_shows_friendly_error_recovery_message() -> None:
    """API/SSE failures surface a friendly retry message, not a raw stack."""
    source = _app_js()
    assert "Could not" in source or "Something went wrong" in source
    assert "try again" in source.lower()
    # SSE onerror has a recovery path (not a silent close only).
    assert 'addEventListener("error"' in source


# --- User control & freedom (reset / new debate) -------------------------


def test_index_has_a_new_debate_reset_control() -> None:
    """A "new debate" control lets the user reset and start over."""
    body = _html().lower()
    assert 'id="new-debate"' in body
    assert "new debate" in body


def test_app_js_wires_the_new_debate_reset_control() -> None:
    """``app.js`` wires the reset control to clear state and start fresh."""
    source = _app_js()
    assert "new-debate" in source
    assert "resetDebate" in source


# --- Help & documentation -------------------------------------------------


def test_index_has_a_help_about_hint() -> None:
    """A short help/about line explains what the app does and how to use it."""
    body = _html().lower()
    assert 'class="help' in body or 'id="help"' in body


# --- Consistency & recognition over recall -------------------------------


def test_index_uses_consistent_human_labels() -> None:
    """Consistent, human terminology: Pro / Con / Moderator / Verdict."""
    body = _html()
    for label in ("Pro", "Con", "Moderator", "Verdict"):
        assert label in body


def test_status_css_is_rtl_safe_logical_properties_only() -> None:
    """New status/help/reset styling uses logical properties only (RTL-safe)."""
    css = _css()
    assert ".status" in css
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
