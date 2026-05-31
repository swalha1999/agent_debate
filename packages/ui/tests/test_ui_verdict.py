"""Tests for the verdict view (task 11.4, issue #76).

The debate's SSE stream ends with a ``verdict`` event then a ``done`` sentinel.
When the stream finishes, the UI shows a *distinct* verdict view rendering the
debate summary, whether the agents agreed/converged, who won (Pro/Con/Tie), and
the token/cost totals. The cleanest source for all of this in one place is the
final ``DebateResult`` (``verdict`` + ``totals``), which the API exposes at
``GET /debates/{id}`` (``DebateState.result``); the view fetches it on ``done``.

A real browser cannot run under pytest, so (as for 11.1-11.3) these tests assert
at the *serving* level: the served HTML exposes a verdict-view region and
``app.js`` carries the wiring that fetches the result and renders winner /
summary / converged / token totals. Browser behaviour is the UI smoke (11.8).
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


def test_index_has_a_verdict_view_region() -> None:
    """The page exposes a distinct verdict-view region with a heading."""
    body = _html().lower()
    assert 'id="verdict"' in body
    assert "verdict" in body


def test_verdict_view_exposes_outcome_containers() -> None:
    """The view exposes containers for winner / summary / converged / tokens."""
    body = _html().lower()
    assert 'id="verdict-winner"' in body
    assert 'id="verdict-summary"' in body
    assert 'id="verdict-converged"' in body
    assert 'id="verdict-tokens"' in body


def test_app_js_fetches_the_final_result_on_done() -> None:
    """On the ``done`` sentinel the view fetches GET /debates/{id} for totals."""
    source = _app_js()
    # The result endpoint (no /stream suffix) carries verdict + totals together.
    assert "${apiBaseUrl()}/debates/" in source
    assert "renderVerdict" in source
    assert 'addEventListener("done"' in source


def test_app_js_renders_winner_summary_converged_tokens() -> None:
    """The verdict render references winner, summary, converged and token fields."""
    source = _app_js()
    assert "verdict.winner" in source
    assert "verdict.summary" in source or "verdict.rationale" in source
    assert "verdict.converged" in source
    assert "total_tokens" in source


def test_app_js_labels_pro_con_tie_outcomes() -> None:
    """Who-won renders clearly as Pro / Con / Tie."""
    source = _app_js().lower()
    assert "pro" in source
    assert "con" in source
    assert "tie" in source


def test_app_js_uses_result_endpoint_not_only_stream() -> None:
    """The result fetch targets ``/debates/{id}`` (the result, not the stream)."""
    source = _app_js()
    assert "resultUrl" in source


def test_verdict_css_is_rtl_safe_logical_properties_only() -> None:
    """Verdict CSS uses logical properties only (no physical left/right)."""
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


def test_verdict_view_has_distinct_styling() -> None:
    """The stylesheet styles the verdict view region distinctly."""
    assert ".verdict" in _css().lower()
