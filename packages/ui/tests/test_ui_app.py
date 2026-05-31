"""Tests for the UI app factory + topic-input page (task 11.1, issue #73).

TDD: these assert the contract before the code exists. The UI is a small
FastAPI app that *serves* a static topic-input frontend; the JS calls the API
browser-side, so these tests never touch the network — they only prove the
serving routes via :class:`~fastapi.testclient.TestClient`.

Scope (11.1): ``GET /`` returns the topic-input page (a form + a topic input +
a "start" control); the API base URL is config-driven and surfaced to the page
(injected into the HTML *and* exposed via ``GET /config``); ``create_app()`` is
a reusable factory. The live transcript view is task 11.2.
"""

from __future__ import annotations

import pytest
from agent_debate.ui.app import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_create_app_returns_fastapi_instance() -> None:
    """``create_app()`` returns a configured :class:`FastAPI` instance."""
    assert isinstance(create_app(), FastAPI)


def test_app_factory_is_reusable() -> None:
    """Two calls yield two independent app instances (factory pattern)."""
    assert create_app() is not create_app()


def test_index_serves_topic_input_page() -> None:
    """``GET /`` returns 200 HTML with a topic input + a start control."""
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    body = response.text.lower()
    assert "<form" in body
    assert "topic" in body
    assert 'id="topic"' in body
    assert "start debate" in body


def test_index_injects_config_driven_api_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The served page carries the config-driven API base URL (env override)."""
    monkeypatch.setenv("API_BASE_URL", "http://example.test:9000")
    client = TestClient(create_app())

    response = client.get("/")

    assert "http://example.test:9000" in response.text


def test_config_endpoint_returns_api_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``GET /config`` returns the config-driven API base URL as JSON."""
    monkeypatch.setenv("API_BASE_URL", "http://example.test:9000")
    client = TestClient(create_app())

    response = client.get("/config")

    assert response.status_code == 200
    assert response.json() == {"api_base_url": "http://example.test:9000"}


def test_config_endpoint_falls_back_to_named_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no env override, ``/config`` reports the named default base URL."""
    from agent_debate.ui.config import DEFAULT_API_BASE_URL

    monkeypatch.delenv("API_BASE_URL", raising=False)
    client = TestClient(create_app())

    assert client.get("/config").json() == {"api_base_url": DEFAULT_API_BASE_URL}


def test_static_assets_are_served() -> None:
    """The CSS/JS static assets are reachable (so the page works)."""
    client = TestClient(create_app())

    assert client.get("/static/style.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200


def test_app_is_importable_and_constructed_at_module_level() -> None:
    """The module-level ``app`` (used by uvicorn) is a built FastAPI instance."""
    from agent_debate.ui.app import app

    assert isinstance(app, FastAPI)
